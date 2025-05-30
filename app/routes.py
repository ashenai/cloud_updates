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
from flask import render_template, flash, redirect, url_for, request, jsonify, current_app
from sqlalchemy import func, extract
from app import db
from app.models import Update, WeeklyInsight, WeeklyTheme
from app.utils.update_analyzer import generate_explanation, format_explanation_text
from app.rag.embeddings import UpdateSearch
from app.scraper.aws_scraper import AWSScraper
from app.scraper.azure_scraper import AzureScraper
from app.scraper.aws_services import AWSServicesFetcher
from app.utils.theme_analyzer_llm import LLMThemeAnalyzer
from app.utils.theme_analyzer import get_week_start
from app.utils.cleaner import clean_all_updates
from app.utils.scraper import scrape_aws_updates, scrape_azure_updates

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

def get_available_weeks():
    """Get a list of available weeks for theme generation.
    
    Returns a list of datetime objects representing the start of each week,
    going back 12 weeks from the current week.
    """
    # Get the start of the current week
    current_week = get_week_start(datetime.utcnow())
    
    # Generate a list of weeks (going back 12 weeks)
    weeks = []
    for i in range(12):
        week_start = current_week - timedelta(days=7 * i)
        weeks.append(week_start)
    
    return weeks

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
        # Get the latest week that has themes
        latest_theme = WeeklyTheme.query.order_by(WeeklyTheme.week_start.desc()).first()
        if latest_theme:
            latest_week = latest_theme.week_start
            themes = WeeklyTheme.query.filter_by(week_start=latest_week).all()
        else:
            themes = []
        
        # Split themes by provider
        aws_themes = [t for t in themes if t.provider == 'aws']
        azure_themes = [t for t in themes if t.provider == 'azure']
        
        # Get latest 3 updates for each provider
        latest_aws_updates = Update.query.filter_by(provider='aws').order_by(Update.published_date.desc()).limit(3).all()
        latest_azure_updates = Update.query.filter_by(provider='azure').order_by(Update.published_date.desc()).limit(3).all()
        
        return render_template(
            'index.html',
            aws_themes=aws_themes,
            azure_themes=azure_themes,
            themes=themes,  # Used to check if any themes exist
            latest_aws_updates=latest_aws_updates,
            latest_azure_updates=latest_azure_updates
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
                    # Try multiple date formats to handle different inputs
                    for date_format in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                        try:
                            selected_week = datetime.strptime(week_param, date_format)
                            break
                        except ValueError:
                            continue
                    else:
                        # If none of the formats worked, raise ValueError
                        raise ValueError(f"Could not parse date: {week_param}")
                        
                    # Ensure we're using the start of the week
                    selected_week = get_week_start(selected_week)
                    print(f"Parsed selected week: {selected_week}")  # Debug print
                except ValueError as e:
                    print(f"Error parsing week parameter: {week_param} - {str(e)}")  # Debug print
                    selected_week = weeks[0] if weeks else get_week_start(datetime.utcnow())
            else:
                # Use most recent week with themes, or current week if none
                selected_week = weeks[0] if weeks else get_week_start(datetime.utcnow())
            
            print(f"Selected week: {selected_week}")  # Debug print
            
            # Get themes for the selected week
            # Use func.date() to compare only the date part
            themes = WeeklyTheme.query.filter(
                func.date(WeeklyTheme.week_start) == func.date(selected_week)
            ).order_by(
                WeeklyTheme.provider,
                WeeklyTheme.relevance_score.desc()
            ).all()
            
            print(f"Found {len(themes)} themes for week {selected_week}")  # Debug print
            for theme in themes:
                print(f"- {theme.theme_name} ({theme.provider})")  # Debug print
            
            # If no themes found for the selected week, check if we need to convert the date
            if not themes and week_param:
                print(f"No themes found for {selected_week}, trying alternative date formats")
                
                # Try to find the week by searching for a close match using only date part
                for week in weeks:
                    if abs((week.date() - selected_week.date()).days) < 7:
                        print(f"Found close match: {week} for {selected_week}")
                        selected_week = week
                        
                        # Get themes for the matched week using date comparison
                        themes = WeeklyTheme.query.filter(
                            func.date(WeeklyTheme.week_start) == func.date(selected_week)
                        ).order_by(
                            WeeklyTheme.provider,
                            WeeklyTheme.relevance_score.desc()
                        ).all()
                        
                        if themes:
                            print(f"Found {len(themes)} themes using close match")
                            break
            
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

    @app.route('/aws_updates')
    @app.route('/aws_updates/page/<int:page>')
    def aws_updates(page=1):
        """Show AWS updates."""
        # Get filter parameters
        selected_categories = request.args.getlist('category')
        
        # Build query
        query = Update.query.filter_by(provider='aws')
        
        # Apply product filter if selected
        if selected_categories:
            query = query.filter(Update.product_name.in_(selected_categories))
        
        # Get paginated results
        updates = query.order_by(Update.published_date.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        total_pages = updates.pages

        # Debug print for first 3 updates
        print("=== AWS Updates Debug ===")
        for upd in updates.items[:3]:
            print(f"Title: {upd.title}")
            print(f"Product: {getattr(upd, 'product_name', None)}")
            print(f"Categories: {getattr(upd, 'categories', None)}")
            print(f"Types: {getattr(upd, 'update_types', None)}")
            print(f"Status: {getattr(upd, 'status', None)}")
            print("---")

        # Get unique product names for filter
        products = db.session.query(Update.product_name).filter(
            Update.provider == 'aws',
            Update.product_name.isnot(None)
        ).distinct().order_by(Update.product_name).all()
        products = [p[0] for p in products if p[0]]  # Remove None values

        return render_template(
            'base_updates.html',
            updates=updates.items,
            provider='aws',
            page=page,
            total_pages=total_pages,
            categories=products,
            selected_categories=selected_categories
        )

    @app.route('/azure_updates')
    @app.route('/azure_updates/page/<int:page>')
    def azure_updates(page=1):
        """Show Azure updates."""
        # Get filter parameters
        selected_products = request.args.getlist('category')  # Keep parameter name for backwards compatibility
        selected_types = request.args.getlist('type')
        selected_statuses = request.args.getlist('status')
        
        # Build query
        query = Update.query.filter_by(provider='azure')
        
        # Apply product filter if selected
        if selected_products:
            # Filter for updates where any of the selected products exist in the product_names array
            product_filters = []
            for product in selected_products:
                # Need to use the _product_names column (JSON string) for filtering
                product_filters.append(Update._product_names.like(f'%"{product}"%'))
            query = query.filter(db.or_(*product_filters))
        
        # Apply type filter if selected
        if selected_types:
            # Filter for updates where any of the selected types exist in the update_types array
            type_filters = []
            for update_type in selected_types:
                # Need to use the _update_types column (JSON string) for filtering
                type_filters.append(Update._update_types.like(f'%"{update_type}"%'))
            query = query.filter(db.or_(*type_filters))
            
        # Apply status filter if selected
        if selected_statuses:
            # Filter for updates where any of the selected statuses exist in the status array
            status_filters = []
            for status in selected_statuses:
                # Need to use the _status column (JSON string) for filtering
                status_filters.append(Update._status.like(f'%"{status}"%'))
            query = query.filter(db.or_(*status_filters))
        
        # Get paginated results
        updates = query.order_by(Update.published_date.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        total_pages = updates.pages

        # Debug print for first 3 updates
        print("=== Azure Updates Debug ===")
        for upd in updates.items[:3]:
            print(f"Title: {upd.title}")
            print(f"Product: {getattr(upd, 'product_name', None)}")
            print(f"Products: {getattr(upd, 'product_names', [])}")
            print(f"Types: {getattr(upd, 'update_types', [])}")
            print(f"Status: {getattr(upd, 'status', [])}")
            print("---")

        # Get unique products, types, and statuses for filters
        products = set()
        types = set()
        statuses = set()
        
        # Add hardcoded status values to ensure they're always available
        statuses.update(['In development', 'In preview', 'Launched'])
        
        azure_updates = Update.query.filter_by(provider='azure').all()
        for update in azure_updates:
            try:
                if hasattr(update, 'product_names') and update.product_names:
                    products.update(update.product_names)
                elif hasattr(update, 'categories') and update.categories:
                    # Fallback to categories if product_names is empty
                    products.update(update.categories)
                    
                if hasattr(update, 'update_types') and update.update_types:
                    types.update(update.update_types)
                    
                if hasattr(update, 'status') and update.status:
                    statuses.update(update.status)
            except Exception as e:
                print(f"Error processing update {update.id}: {str(e)}")
        
        print(f"Found {len(products)} products, {len(types)} types, and {len(statuses)} statuses")

        return render_template(
            'base_updates.html',
            updates=updates.items,
            provider='azure',
            page=page,
            total_pages=total_pages,
            categories=sorted(products),  # Keep template variable name for backwards compatibility
            types=sorted(types),
            statuses=sorted(statuses),
            selected_categories=selected_products,  # Keep template variable name for backwards compatibility
            selected_types=selected_types,
            selected_statuses=selected_statuses
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
            
            # Dictionaries for tracking cumulative counts across all weeks
            cumulative_aws_products = {}
            cumulative_azure_categories = {}
            
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
                    # Calculate weekly AWS products
                    weekly_aws_products = {}
                    for update in aws_updates:
                        if update.product_name:
                            weekly_aws_products[update.product_name] = weekly_aws_products.get(update.product_name, 0) + 1
                            # Also update cumulative counts
                            cumulative_aws_products[update.product_name] = cumulative_aws_products.get(update.product_name, 0) + 1
                    
                    # Calculate weekly Azure categories
                    weekly_azure_categories = {}
                    for update in azure_updates:
                        # For Azure, use the categories but ignore status categories
                        categories = [cat for cat in update.categories if cat not in ignored_categories]
                        for category in categories:
                            weekly_azure_categories[category] = weekly_azure_categories.get(category, 0) + 1
                            # Also update cumulative counts
                            cumulative_azure_categories[category] = cumulative_azure_categories.get(category, 0) + 1
                    
                    # Get top weekly products/categories for this specific week
                    aws_top_products = [
                        {"name": name, "count": count}
                        for name, count in sorted(weekly_aws_products.items(), key=lambda x: x[1], reverse=True)[:5]
                    ]
                    
                    azure_top_categories = [
                        {"name": name, "count": count}
                        for name, count in sorted(weekly_azure_categories.items(), key=lambda x: x[1], reverse=True)[:5]
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
            
            # Calculate cumulative top products/categories across all weeks
            cumulative_aws_top_products = [
                {"name": name, "count": count}
                for name, count in sorted(cumulative_aws_products.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
            
            cumulative_azure_top_categories = [
                {"name": name, "count": count}
                for name, count in sorted(cumulative_azure_categories.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
            
            # Create an insight for the "All Time" data
            all_time_insight = WeeklyInsight(
                week_start=start_date,
                week_end=end_date,
                aws_updates=Update.query.filter_by(provider='aws').count(),
                azure_updates=Update.query.filter_by(provider='azure').count(),
                aws_top_products=cumulative_aws_top_products,
                azure_top_categories=cumulative_azure_top_categories,
                is_cumulative=True  # Add a flag to identify this as cumulative data
            )
            db.session.add(all_time_insight)
            
            db.session.commit()
            flash('Successfully generated insights with cumulative totals.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error generating insights: {str(e)}', 'error')
        
        return redirect(url_for('admin'))

    @app.route('/admin/generate_themes', methods=['POST'])
    def admin_generate_themes():
        """Generate themes from updates."""
        try:
            # Get the selected week from the form
            selected_week_str = request.form.get('week')
            
            # Debug print form data
            print("\nForm data received:")
            for key, value in request.form.items():
                print(f"{key}: {value}")
            
            # force_regenerate will only be present in form data if checkbox is checked
            force_regenerate = request.form.get('force_regenerate') is not None
            print(f"Force regenerate value: {force_regenerate}")
            
            if not selected_week_str:
                flash('No week selected. Please select a week.', 'error')
                return redirect(url_for('admin'))
                
            # Parse the selected week
            try:
                selected_week = datetime.fromisoformat(selected_week_str)
                print(f"Selected week: {selected_week}")  # Debug print
            except ValueError:
                flash('Invalid week format. Please try again.', 'error')
                return redirect(url_for('admin'))
                
            # Calculate the end of the selected week
            week_end = selected_week + timedelta(days=7)
            
            # Check if themes already exist for this week using date comparison
            existing_themes = WeeklyTheme.query.filter(
                func.date(WeeklyTheme.week_start) == func.date(selected_week)
            ).all()
            
            if existing_themes and not force_regenerate:
                print(f"Themes exist and force_regenerate is {force_regenerate}")  # Debug print
                flash(f'Themes already exist for week of {selected_week.strftime("%b %d, %Y")}. Use force regenerate if you want to recreate them.', 'info')
                return redirect(url_for('admin'))
            
            # Get updates for the selected week using date comparison
            updates = Update.query.filter(
                Update.published_date >= func.date(selected_week),
                Update.published_date < func.date(week_end)
            ).all()
            
            if not updates:
                flash(f'No updates found for the week of {selected_week.strftime("%b %d, %Y")}.', 'warning')
                return redirect(url_for('admin'))
            
            print(f"\nFound {len(updates)} updates for week of {selected_week.strftime('%b %d, %Y')}")  # Debug print
            
            # Group updates by provider
            aws_updates = [u for u in updates if u.provider.lower() == 'aws']
            azure_updates = [u for u in updates if u.provider.lower() == 'azure']
            
            # Only delete existing themes if we're actually going to generate new ones
            # This happens either when force_regenerate is true or when no themes existed
            if force_regenerate or not existing_themes:
                print(f"Deleting existing themes (force_regenerate: {force_regenerate}, existing_themes: {bool(existing_themes)})")  # Debug print
                WeeklyTheme.query.filter(
                    func.date(WeeklyTheme.week_start) == func.date(selected_week)
                ).delete(synchronize_session='fetch')
            
            # Generate themes for each provider if they have updates
            analyzer = LLMThemeAnalyzer()
            for provider, provider_updates in [('aws', aws_updates), ('azure', azure_updates)]:
                if provider_updates:
                    print(f"\nProcessing {provider} updates for week {selected_week}")  # Debug print
                    try:
                        themes = analyzer.generate_themes(provider_updates)
                          # Save themes
                        for theme_data in themes:
                            # Create WeeklyTheme
                            weekly_theme = WeeklyTheme(
                                week_start=selected_week,
                                provider=theme_data['provider'],
                                theme_name=theme_data['name'],
                                description=theme_data['description'],
                                relevance_score=theme_data['score'],
                                update_count=theme_data['update_count'],
                                services=theme_data.get('services', [])
                            )
                            print(f"Creating WeeklyTheme: {weekly_theme.theme_name} for week {weekly_theme.week_start}")  # Debug print
                            print(f"Services for this theme: {theme_data.get('services', [])}")  # Debug print
                            db.session.add(weekly_theme)
                        
                    except Exception as e:
                        print(f"Error generating themes for {provider} in week {selected_week}: {str(e)}")  # Debug print
                        continue
            
            try:
                db.session.commit()
                print("\nSuccessfully committed themes to database")  # Debug print
                # Query and print all weekly themes after commit
                all_themes = WeeklyTheme.query.filter(
                    func.date(WeeklyTheme.week_start) == func.date(selected_week)
                ).all()
                print(f"\nWeekly themes for {selected_week.strftime('%b %d, %Y')}:")
                for t in all_themes:
                    print(f"- {t.theme_name} (Provider: {t.provider})")
                
                flash(f'Successfully generated themes for week of {selected_week.strftime("%b %d, %Y")}.', 'success')
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

    @app.route('/debug/themes')
    def debug_themes():
        """Debug endpoint to check theme status."""
        try:
            current_week = get_week_start(datetime.utcnow())
            themes = WeeklyTheme.query.all()
            
            debug_info = {
                'current_week': current_week.isoformat(),
                'total_themes': len(themes),
                'themes_by_week': {}
            }
            
            for theme in themes:
                week = theme.week_start.isoformat()
                if week not in debug_info['themes_by_week']:
                    debug_info['themes_by_week'][week] = []
                debug_info['themes_by_week'][week].append({
                    'name': theme.theme_name,
                    'provider': theme.provider,
                    'score': theme.relevance_score,
                    'update_count': theme.update_count
                })
            
            return jsonify(debug_info)
        except Exception as e:
            current_app.logger.error(f"Error in debug_themes endpoint: {str(e)}", exc_info=True)
            return jsonify({'error': 'An internal error occurred'}), 500

    @app.route('/reprocess-aws')
    def reprocess_aws():
        """Reprocess existing AWS updates with the improved extraction logic."""
        try:
            # Create processor
            from app.utils.update_processor import UpdateProcessor
            processor = UpdateProcessor()
            
            # Get all AWS updates
            aws_updates = Update.query.filter_by(provider='aws').all()
            print(f"Found {len(aws_updates)} AWS updates to reprocess")
            
            # Reprocess each update
            count = 0
            for update in aws_updates:
                # Clean description
                from app.scraper.aws_scraper import AWSScraper
                scraper = AWSScraper()
                original_length = len(update.description)
                update.description = scraper.clean_html(update.description)
                new_length = len(update.description)
                print(f"Description length: {original_length} -> {new_length} chars")
                
                # Extract product name
                metadata = processor.process_aws_update({
                    'title': update.title,
                    'description': update.description
                })
                
                # Update product name
                if metadata['product_name']:
                    update.product_name = metadata['product_name']
                    count += 1
                    print(f"Product found: {update.title} -> {metadata['product_name']}")
                else:
                    print(f"No product found for: {update.title}")
            
            # Commit changes
            db.session.commit()
            
            return f"Successfully reprocessed {count} AWS updates with new product names out of {len(aws_updates)} total."
        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return f"Error reprocessing AWS updates: {str(e)}"

    @app.route('/reprocess-azure')
    def reprocess_azure():
        """Reprocess existing Azure updates with the improved categorization logic."""
        try:
            # Create processor
            from app.utils.update_processor import UpdateProcessor
            processor = UpdateProcessor()
            
            # Get all Azure updates
            azure_updates = Update.query.filter_by(provider='azure').all()
            print(f"Found {len(azure_updates)} Azure updates to reprocess")
            
            # Reprocess each update
            count = 0
            for update in azure_updates:
                # Extract metadata using the new categorization logic
                metadata = processor.process_azure_update({
                    'title': update.title,
                    'description': update.description,
                    'categories': update.categories
                })
                
                # Update fields
                update.product_name = metadata['product_name']
                update.product_names = metadata['product_names']
                update.categories = metadata['categories']
                update.update_types = metadata['update_types']
                update.status = metadata['status']
                count += 1
                
                print(f"Processed: {update.title}")                
                print(f"  - Primary Product: {update.product_name}")
                print(f"  - All Products: {update.product_names}")
                print(f"  - Update Types: {update.update_types}")
                print(f"  - Status: {update.status}")
            
            # Commit changes
            db.session.commit()
            
            return f"Successfully reprocessed {count} Azure updates with new categorization."
        except Exception as e:            
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return f"Error reprocessing Azure updates: {str(e)}"
            
    @app.route('/health')
    def health_check():
        return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}), 200
        
    @app.route('/insights')
    def insights():
        """Show insights page."""
        # Get selected week if provided, otherwise default to "all-time"
        selected_week_str = request.args.get('week', 'all-time')
        
        # Get weekly insights (excluding cumulative ones)
        insights = WeeklyInsight.query.filter_by(is_cumulative=False).order_by(WeeklyInsight.week_start.desc()).all()
        
        # Prepare data for trend charts
        weeks = []
        aws_counts = []
        azure_counts = []
        
        # Prepare data for week picker
        available_weeks = []
        
        for insight in insights:
            # Format for trend chart
            weeks.append(insight.week_start.strftime('%b %d'))
            aws_counts.append(insight.aws_updates)
            azure_counts.append(insight.azure_updates)
            
            # Format for week picker dropdown
            week_str = insight.week_start.strftime('%Y-%m-%d')
            week_display = insight.week_start.strftime('%b %d, %Y')
            available_weeks.append({
                'value': week_str,
                'display': week_display
            })
        
        # Reverse lists to show chronological order
        weeks.reverse()
        aws_counts.reverse()
        azure_counts.reverse()
        
        # Get cumulative insight for all-time data
        cumulative_insight = WeeklyInsight.query.filter_by(is_cumulative=True).first()
        
        # By default, show all-time data
        selected_insight = cumulative_insight
          # If a specific week is selected, find that insight
        if selected_week_str != 'all-time':
            try:
                selected_date = datetime.strptime(selected_week_str, '%Y-%m-%d')
                # Use string comparisons for more reliable date matching
                week_start_str = selected_date.strftime('%Y-%m-%d')
                
                # First try exact match with string comparison of date
                for insight in insights:
                    if insight.week_start.strftime('%Y-%m-%d') == week_start_str:
                        selected_insight = insight
                        break
                else:
                    # Fallback to range query if no exact match found
                    selected_insight = WeeklyInsight.query.filter(
                        WeeklyInsight.is_cumulative == False,
                        WeeklyInsight.week_start >= selected_date,
                        WeeklyInsight.week_start < selected_date + timedelta(days=7)
                    ).first()
                
                # If not found, fall back to cumulative
                if not selected_insight:
                    selected_insight = cumulative_insight
                    selected_week_str = 'all-time'
            except ValueError:
                # Invalid date format, use cumulative
                selected_insight = cumulative_insight
                selected_week_str = 'all-time'
        
        # Debug: Print insights data to help identify any issues
        print(f"Selected week: {selected_week_str}")
        print(f"Selected insight: {selected_insight}")
        print(f"Available weeks: {available_weeks}")        
        return render_template(
            'insights.html',  # Using the original template name
            weeks=weeks,
            aws_counts=aws_counts,
            azure_counts=azure_counts,
            selected_insight=selected_insight,
            cumulative_insight=cumulative_insight,
            selected_week=selected_week_str,
            available_weeks=available_weeks
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
    
    def get_week_start(dt):
        """Get the start of the week (Monday) for a given date/datetime."""
        # Convert to datetime if date
        if isinstance(dt, date) and not isinstance(dt, datetime):
            dt = datetime.combine(dt, datetime.min.time())
        
        # Get Monday of the week (weekday 0 is Monday)
        monday = dt - timedelta(days=dt.weekday())
        
        # Normalize to midnight UTC
        return monday.replace(hour=0, minute=0, second=0, microsecond=0)

    @app.route('/api/update/<int:update_id>/explain')    
    def get_update_explanation(update_id):
        try:
            update = Update.query.get_or_404(update_id)
            
            if not update.explanation:
                # If no explanation exists, generate one using Claude
                try:
                    explanation = generate_explanation(update.title)
                    update.explanation = explanation
                    db.session.commit()
                except Exception as e:
                    current_app.logger.error(f"Error generating explanation: {str(e)}")
                    return jsonify({
                        'error': f"Failed to generate explanation: {str(e)}"
                    }), 500
            
            if not update.explanation:
                return jsonify({
                    'error': 'Could not generate explanation for this update.'
                }), 500
            
            # First apply traditional formatting (for backward compatibility)
            formatted_explanation = update.explanation
            if formatted_explanation:
                # Replace double line breaks with paragraph tags
                formatted_explanation = '<p>' + formatted_explanation.replace('\r\n\r\n', '</p><p>') + '</p>'
                # Replace single line breaks with <br> tags
                formatted_explanation = formatted_explanation.replace('\r\n', '<br>')
                # Handle the case where we might have \n\n instead of \r\n\r\n
                formatted_explanation = formatted_explanation.replace('<p><br></p>', '<p>')
            
            # For newly generated explanations or if we want enhanced formatting,
            # also try the spaCy-based paragraph detection if the text doesn't already have HTML
            if update.explanation and '<p>' not in update.explanation:
                try:
                    improved_explanation = format_explanation_text(update.explanation)
                    if improved_explanation:
                        formatted_explanation = improved_explanation
                except Exception as format_error:
                    current_app.logger.warning(f"SpaCy formatting failed, using traditional formatting: {str(format_error)}")
                
            return jsonify({'explanation': formatted_explanation})
            
        except Exception as e:
            current_app.logger.error(f"Error in get_update_explanation: {str(e)}")
            return jsonify({
                'error': f"Failed to fetch explanation: {str(e)}"
            }), 500

    @app.route('/api/update/<int:update_id>/generate_explanation', methods=['POST'])
    def generate_update_explanation(update_id):
        # Forward to the existing explain endpoint functionality
        return get_update_explanation(update_id)

    @app.route('/admin/generate_explanations', methods=['POST'])
    def admin_generate_explanations():
        """Generate explanations for updates."""
        try:
            force_regenerate = bool(request.form.get('force_regenerate'))
            
            # Build query for updates without explanations or all updates if force_regenerate
            query = Update.query
            if not force_regenerate:
                query = query.filter(Update.explanation.is_(None))
            
            updates = query.order_by(Update.published_date.desc()).all()
            total_updates = len(updates)
            
            if not updates:
                flash('No updates found that need explanations.', 'info')
                return redirect(url_for('admin'))
            processed = 0
            for update in updates:
                try:
                    # Generate the raw explanation
                    raw_explanation = generate_explanation(update.title)
                    
                    # Store the raw text - formatting will be applied when retrieved
                    update.explanation = raw_explanation
                    processed += 1
                    
                except Exception as e:
                    current_app.logger.error(f"Error generating explanation for update {update.id}: {str(e)}")
                    continue
                
                # Commit in batches of 10
                if processed % 10 == 0:
                    try:
                        db.session.commit()
                    except Exception as commit_error:
                        current_app.logger.error(f"Error committing batch: {str(commit_error)}")
                        db.session.rollback()
            
            # Final commit for remaining changes
            try:
                db.session.commit()
                flash(f'Successfully generated {processed} explanations out of {total_updates} updates.', 'success')
            except Exception as commit_error:
                db.session.rollback()
                flash(f'Error saving explanations: {str(commit_error)}', 'error')
                
        except Exception as e:
            flash(f'Error generating explanations: {str(e)}', 'error')
        
        return redirect(url_for('admin'))
