"""
Copyright 2025 Aavind K Shenai

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

DISCLAIMER:
This code was generated using artificial intelligence. While efforts have been made
to ensure its accuracy and functionality, users should:
1. Review and test the code thoroughly before deployment
2. Be aware that AI-generated code may contain unexpected behaviors
3. Use this code at their own risk
4. Not rely on this code for critical systems without proper validation
"""

from datetime import datetime, timedelta, date
from flask import render_template, flash, redirect, url_for, request, jsonify
from sqlalchemy import func, extract
from app.models import Update, WeeklyTheme, WeeklyInsight, Theme
from app.rag.embeddings import UpdateSearch
from app import db
from app.utils.theme_analyzer import get_week_start
from app.utils.scraper import scrape_aws_updates, scrape_azure_updates
from app.utils.cleaner import clean_all_updates, clean_aws_duplicates, clean_azure_duplicates
from app.utils.theme_analyzer_llm import LLMThemeAnalyzer

# Initialize search system
update_search = UpdateSearch()

def get_update_counts():
    """Get the total counts of AWS and Azure updates."""
    aws_count = Update.query.filter_by(provider='aws').count()
    azure_count = Update.query.filter_by(provider='azure').count()
    return aws_count, azure_count

def rebuild_search_index():
    """Rebuild the search index with all updates."""
    updates = Update.query.all()
    update_search.build_index(updates)

def init_routes(app):
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}

    @app.context_processor
    def utility_processor():
        return {
            'min': min,
            'max': max
        }

    @app.route('/')
    def index():
        """Home page."""
        # Get current week's themes
        current_week = get_week_start(datetime.utcnow())
        themes = WeeklyTheme.query.filter_by(week_start=current_week).all()
        
        # Split themes by provider
        aws_themes = [t for t in themes if t.provider == 'aws']
        azure_themes = [t for t in themes if t.provider == 'azure']
        
        return render_template(
            'index.html',
            aws_themes=aws_themes,
            azure_themes=azure_themes,
            themes=themes  # Used to check if any themes exist
        )

    @app.route('/themes')
    def themes():
        """Display themes for a specific week."""
        try:
            # Get all available weeks first
            weeks_with_themes = db.session.query(
                WeeklyTheme.week_start
            ).distinct().order_by(
                WeeklyTheme.week_start.desc()
            ).all()
            
            weeks = [week[0] for week in weeks_with_themes]
            print(f"Available weeks: {weeks}")  # Debug print
            
            # Get week parameter or use most recent week
            week_param = request.args.get('week')
            print(f"Week param: {week_param}")  # Debug print
            
            if week_param:
                try:
                    selected_week = datetime.strptime(week_param, '%Y-%m-%d')
                    selected_week = get_week_start(selected_week)
                except ValueError:
                    print(f"Error parsing week parameter: {week_param}")  # Debug print
                    selected_week = weeks[0] if weeks else get_week_start(datetime.utcnow())
            else:
                # Use most recent week with themes, or current week if none
                selected_week = weeks[0] if weeks else get_week_start(datetime.utcnow())
            
            print(f"Selected week: {selected_week}")  # Debug print
            
            # Get themes for the selected week
            themes = WeeklyTheme.query.filter(
                WeeklyTheme.week_start == selected_week
            ).order_by(
                WeeklyTheme.provider,
                WeeklyTheme.relevance_score.desc()
            ).all()
            
            print(f"Found {len(themes)} themes for week {selected_week}")  # Debug print
            for theme in themes:
                print(f"- {theme.theme_name} ({theme.provider})")  # Debug print
            
            return render_template(
                'themes.html',
                themes=themes,
                selected_week=selected_week,
                weeks=weeks
            )
            
        except Exception as e:
            print(f"Error in themes route: {str(e)}")  # Debug print
            import traceback
            traceback.print_exc()
            flash('Error loading themes. Please try again.', 'error')
            return redirect(url_for('index'))

    @app.route('/aws-updates')
    @app.route('/aws-updates/page/<int:page>')
    def aws_updates(page=1):
        """Show AWS updates."""
        per_page = 20
        updates = Update.query.filter_by(provider='aws').order_by(Update.published_date.desc())
        total = updates.count()
        total_pages = (total + per_page - 1) // per_page
        
        updates = updates.paginate(page=page, per_page=per_page, error_out=False)
        
        return render_template(
            'base_updates.html',
            updates=updates.items,
            provider='aws',
            page=page,
            total_pages=total_pages
        )

    @app.route('/azure-updates')
    @app.route('/azure-updates/page/<int:page>')
    def azure_updates(page=1):
        """Show Azure updates."""
        per_page = 20
        updates = Update.query.filter_by(provider='azure').order_by(Update.published_date.desc())
        total = updates.count()
        total_pages = (total + per_page - 1) // per_page
        
        updates = updates.paginate(page=page, per_page=per_page, error_out=False)
        
        return render_template(
            'base_updates.html',
            updates=updates.items,
            provider='azure',
            page=page,
            total_pages=total_pages
        )

    @app.route('/admin/generate_insights', methods=['POST'])
    def admin_generate_insights():
        """Generate insights from updates."""
        try:
            # Clear existing insights
            WeeklyInsight.query.delete()
            
            # Find the earliest and latest update dates
            earliest_update = Update.query.order_by(Update.published_date.asc()).first()
            latest_update = Update.query.order_by(Update.published_date.desc()).first()
            
            if not earliest_update or not latest_update:
                flash('No updates found to generate insights from.', 'error')
                return redirect(url_for('admin'))
            
            # Start from the beginning of the week of the earliest update
            start_date = get_week_start(earliest_update.published_date)
            
            # End at the end of the current week
            end_date = get_week_start(datetime.utcnow()) + timedelta(days=7)
            
            # Define categories to ignore
            ignored_categories = {'In preview', 'Launched', 'General availability', 'Generally available'}
            
            # Generate insights for each week
            current_week = start_date
            while current_week < end_date:
                week_end = current_week + timedelta(days=7)
                
                # Get updates for this week
                aws_updates = Update.query.filter(
                    Update.provider == 'aws',
                    Update.published_date >= current_week,
                    Update.published_date < week_end
                ).all()
                
                azure_updates = Update.query.filter(
                    Update.provider == 'azure',
                    Update.published_date >= current_week,
                    Update.published_date < week_end
                ).all()
                
                # Count updates
                aws_count = len(aws_updates)
                azure_count = len(azure_updates)
                
                if aws_count > 0 or azure_count > 0:
                    # Get top AWS products
                    aws_products = {}
                    for update in aws_updates:
                        if update.product_name:
                            aws_products[update.product_name] = aws_products.get(update.product_name, 0) + 1
                    
                    aws_top_products = [
                        {"name": name, "count": count}
                        for name, count in sorted(aws_products.items(), key=lambda x: x[1], reverse=True)[:5]
                    ]
                    
                    # Get top Azure categories
                    azure_categories = {}
                    for update in azure_updates:
                        # For Azure, use the categories but ignore status categories
                        categories = [cat for cat in update.categories if cat not in ignored_categories]
                        for category in categories:
                            azure_categories[category] = azure_categories.get(category, 0) + 1
                    
                    azure_top_categories = [
                        {"name": name, "count": count}
                        for name, count in sorted(azure_categories.items(), key=lambda x: x[1], reverse=True)[:5]
                    ]
                    
                    # Create insight
                    insight = WeeklyInsight(
                        week_start=current_week,
                        week_end=week_end,
                        aws_updates=aws_count,
                        azure_updates=azure_count,
                        aws_top_products=aws_top_products,
                        azure_top_categories=azure_top_categories
                    )
                    db.session.add(insight)
                
                current_week = week_end
            
            db.session.commit()
            flash('Successfully generated insights.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error generating insights: {str(e)}', 'error')
        
        return redirect(url_for('admin'))

    @app.route('/insights')
    def insights():
        """Show insights page."""
        # Get weekly insights
        insights = WeeklyInsight.query.order_by(WeeklyInsight.week_start.desc()).all()
        
        # Prepare data for charts
        weeks = []
        aws_counts = []
        azure_counts = []
        
        for insight in insights:  
            weeks.append(insight.week_start.strftime('%b %d'))
            aws_counts.append(insight.aws_updates)
            azure_counts.append(insight.azure_updates)
        
        # Reverse lists to show chronological order
        weeks.reverse()
        aws_counts.reverse()
        azure_counts.reverse()
        
        # Get latest insight for product/category charts
        latest_insight = WeeklyInsight.query.order_by(WeeklyInsight.week_start.desc()).first()
        
        return render_template(
            'insights.html',
            weeks=weeks,
            aws_counts=aws_counts,
            azure_counts=azure_counts,
            latest_insight=latest_insight
        )

    @app.route('/admin')
    def admin():
        """Admin dashboard."""
        # Get available weeks for theme generation
        available_weeks = get_available_weeks()
        
        # Get current week as default selection
        selected_week = get_week_start(datetime.utcnow())
        
        # Get stats for both providers
        total_aws = Update.query.filter_by(provider='aws').count()
        total_azure = Update.query.filter_by(provider='azure').count()
        
        # Get latest updates
        latest_aws = Update.query.filter_by(provider='aws').order_by(Update.published_date.desc()).first()
        latest_azure = Update.query.filter_by(provider='azure').order_by(Update.published_date.desc()).first()
        
        return render_template(
            'admin.html',
            total_aws=total_aws,
            total_azure=total_azure,
            latest_aws=latest_aws,
            latest_azure=latest_azure,
            available_weeks=available_weeks,
            selected_week=selected_week
        )

    @app.route('/admin/scrape/aws', methods=['POST'])
    def admin_scrape_aws_updates():
        """Scrape AWS updates."""
        try:
            count = scrape_aws_updates()
            flash(f'Successfully fetched {count} AWS updates.', 'success')
        except Exception as e:
            flash(f'Error fetching AWS updates: {str(e)}', 'error')
        
        return redirect(url_for('admin'))

    @app.route('/admin/scrape/azure', methods=['POST'])
    def admin_scrape_azure_updates():
        """Scrape Azure updates."""
        try:
            count = scrape_azure_updates()
            flash(f'Successfully fetched {count} Azure updates.', 'success')
        except Exception as e:
            flash(f'Error fetching Azure updates: {str(e)}', 'error')
        
        return redirect(url_for('admin'))

    @app.route('/admin/refresh', methods=['POST'])
    def admin_refresh():
        try:
            # AWS Updates
            aws_scraper = AWSScraper()
            aws_updates = aws_scraper.scrape()
            aws_count = 0
            for update in aws_updates:
                # Check if update already exists
                existing_update = Update.query.filter_by(
                    provider='aws',
                    title=update['title'],
                    published_date=update['published_date']
                ).first()
                
                if not existing_update:
                    new_update = Update(
                        provider=update['provider'],
                        title=update['title'],
                        description=update['description'],
                        url=update['url'],
                        published_date=update['published_date'],
                        categories=update['categories'],
                        product_name=update['product_name'],
                        update_types=update['update_types']
                    )
                    db.session.add(new_update)
                    aws_count += 1

            # Azure Updates
            azure_scraper = AzureScraper()
            azure_updates = azure_scraper.scrape()
            azure_count = 0
            for update in azure_updates:
                # Check if update already exists
                existing_update = Update.query.filter_by(
                    provider='azure',
                    title=update.title,
                    published_date=update.published_date
                ).first()
                
                if not existing_update:
                    db.session.add(update)
                    azure_count += 1

            db.session.commit()
            flash(f'Successfully fetched {aws_count} new AWS updates and {azure_count} new Azure updates!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error fetching updates: {str(e)}', 'error')
        
        return redirect(url_for('admin'))

    @app.route('/admin/generate_themes', methods=['POST'])
    def admin_generate_themes():
        """Generate themes from updates."""
        try:
            # Clear existing themes
            Theme.query.delete()
            WeeklyTheme.query.delete()
            
            # Get recent updates (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            updates = Update.query.filter(Update.published_date >= thirty_days_ago).all()
            
            if not updates:
                flash('No recent updates found to generate themes from.', 'error')
                return redirect(url_for('admin'))
            
            # Group updates by week
            updates_by_week = {}
            for update in updates:
                week_start = get_week_start(update.published_date)
                if week_start not in updates_by_week:
                    updates_by_week[week_start] = []
                updates_by_week[week_start].append(update)
            
            print(f"\nFound updates for weeks: {list(updates_by_week.keys())}")  # Debug print
            
            # Generate themes for each week
            analyzer = LLMThemeAnalyzer()
            for week_start, week_updates in updates_by_week.items():
                print(f"\nGenerating themes for week of {week_start}")  # Debug print
                print(f"Number of updates: {len(week_updates)}")  # Debug print
                
                # Group updates by provider
                aws_updates = [u for u in week_updates if u.provider.lower() == 'aws']
                azure_updates = [u for u in week_updates if u.provider.lower() == 'azure']
                
                # Generate themes for each provider if they have updates
                for provider, provider_updates in [('aws', aws_updates), ('azure', azure_updates)]:
                    if provider_updates:
                        print(f"\nProcessing {provider} updates for week {week_start}")  # Debug print
                        print(f"Number of {provider} updates: {len(provider_updates)}")  # Debug print
                        
                        try:
                            themes = analyzer.generate_themes(provider_updates)
                            
                            # Save themes
                            for theme_data in themes:
                                # Save to Theme model (global themes)
                                theme = Theme(
                                    name=theme_data['name'],
                                    description=theme_data['description'],
                                    provider=theme_data['provider'],
                                    services=theme_data['services'],
                                    update_count=theme_data['update_count'],
                                    score=theme_data['score']
                                )
                                db.session.add(theme)
                                
                                # Create WeeklyTheme
                                weekly_theme = WeeklyTheme(
                                    week_start=week_start,  # Use the week we're currently processing
                                    provider=theme_data['provider'],
                                    theme_name=theme_data['name'],
                                    description=theme_data['description'],
                                    relevance_score=theme_data['score'],
                                    update_count=theme_data['update_count']
                                )
                                print(f"Creating WeeklyTheme: {weekly_theme.theme_name} for week {weekly_theme.week_start}")  # Debug print
                                db.session.add(weekly_theme)
                            
                        except Exception as e:
                            print(f"Error generating themes for {provider} in week {week_start}: {str(e)}")  # Debug print
                            continue
            
            try:
                db.session.commit()
                print("\nSuccessfully committed themes to database")  # Debug print
                # Query and print all weekly themes after commit
                all_themes = WeeklyTheme.query.all()
                print(f"\nAll weekly themes in database:")
                for t in all_themes:
                    print(f"- {t.theme_name} (Week: {t.week_start}, Provider: {t.provider})")
                
                flash('Successfully generated themes using Claude.', 'success')
            except Exception as commit_error:
                print(f"Error committing to database: {str(commit_error)}")
                db.session.rollback()
                raise
            
        except Exception as e:
            db.session.rollback()
            print(f"Error in theme generation: {str(e)}")  # Debug print
            flash(f'Error generating themes: {str(e)}', 'error')
        
        return redirect(url_for('admin'))

    @app.route('/admin/update_aws_products', methods=['POST'])
    def admin_update_aws_products():
        try:
            aws_services_fetcher = AWSServicesFetcher()
            services = aws_services_fetcher.get_services(refresh=True)
            flash(f'Successfully updated AWS products list! Found {len(services)} products.', 'success')
        except Exception as e:
            flash(f'Error updating AWS products list: {str(e)}', 'error')
        return redirect(url_for('admin'))

    @app.route('/admin/cleanup', methods=['POST'])
    def admin_cleanup():
        """Clean duplicate updates."""
        try:
            removed = clean_all_updates()
            flash(f'Successfully cleaned {removed} duplicate updates.', 'success')
        except Exception as e:
            flash(f'Error cleaning updates: {str(e)}', 'error')
        
        return redirect(url_for('admin'))

    @app.route('/search')
    def search():
        query = request.args.get('q', '')
        if not query:
            return render_template('search.html')
        
        # Ensure index is built
        if not update_search.updates:
            updates = Update.query.all()
            update_search.build_index(updates)
        
        # Perform semantic search
        results = update_search.search(query, k=10)
        
        # Log search metrics
        current_app.logger.info(f"Search query: '{query}' returned {len(results)} results")
        if results:
            current_app.logger.info(f"Top result score: {results[0]['score']:.2f}")
        
        return render_template('search.html', query=query, results=results)

    @app.route('/admin/rebuild_search')
    def admin_rebuild_search():
        try:
            # Get all updates
            updates = Update.query.all()
            
            # Rebuild the search index
            update_search.build_index(updates)
            
            # Log success
            current_app.logger.info(f"Successfully rebuilt search index with {len(updates)} updates")
            flash('Successfully rebuilt the search index!', 'success')
        except Exception as e:
            current_app.logger.error(f"Error rebuilding search index: {str(e)}")
            flash(f'Error rebuilding search index: {str(e)}', 'error')
        
        return redirect(url_for('admin'))

    @app.route('/api/calendar-events')
    def calendar_events():
        """Get weeks with updates as calendar events."""
        # Get all update dates
        updates = Update.query.with_entities(
            Update.published_date, 
            Update.provider,
            func.count(Update.id).label('count')
        ).group_by(
            func.date_trunc('week', Update.published_date),
            Update.provider
        ).all()

        events = []
        for date, provider, count in updates:
            week_start = get_week_start(date)
            week_end = week_start + timedelta(days=6)
            
            events.append({
                'title': f'{provider.upper()}: {count} updates',
                'start': week_start.strftime('%Y-%m-%d'),
                'end': week_end.strftime('%Y-%m-%d'),
                'url': url_for('themes', week=week_start.strftime('%Y-%m-%d')),
                'backgroundColor': '#007bff' if provider == 'aws' else '#dc3545',
                'borderColor': '#0056b3' if provider == 'aws' else '#a71d2a'
            })
        
        return jsonify(events)

    @app.route('/debug')
    def debug():
        aws_updates = Update.query.filter_by(provider='aws').order_by(Update.published_date.desc()).limit(3).all()
        azure_updates = Update.query.filter_by(provider='azure').order_by(Update.published_date.desc()).limit(3).all()
        
        total_aws, total_azure = get_update_counts()
        
        debug_info = {
            'counts': {
                'aws': total_aws,
                'azure': total_azure
            },
            'sample_aws': [{
                'title': u.title,
                'date': u.published_date.isoformat(),
                'provider': u.provider,
                'categories': u.categories,
                'update_types': u.update_types
            } for u in aws_updates],
            'sample_azure': [{
                'title': u.title,
                'date': u.published_date.isoformat(),
                'provider': u.provider,
                'categories': u.categories,
                'update_types': u.update_types
            } for u in azure_updates]
        }
        return jsonify(debug_info)

    def get_available_weeks():
        """Get list of available weeks from updates."""
        # Get all update dates
        dates = [r.published_date for r in Update.query.with_entities(Update.published_date).all()]
        if not dates:
            return [get_week_start(datetime.utcnow())]
        
        # Get min and max dates
        min_date = min(dates)
        max_date = max(dates)
        
        # Generate list of weeks
        weeks = []
        current = get_week_start(min_date)
        while current <= max_date:
            weeks.append(current)
            current += timedelta(days=7)
        
        return weeks

    def get_week_start(dt):
        """Get the start of the week (Monday) for a given date/datetime."""
        # Convert to datetime if date
        if isinstance(dt, date) and not isinstance(dt, datetime):
            dt = datetime.combine(dt, datetime.min.time())
        
        # Get Monday of the week (weekday 0 is Monday)
        monday = dt - timedelta(days=dt.weekday())
        
        # Normalize to midnight UTC
        return monday.replace(hour=0, minute=0, second=0, microsecond=0)
