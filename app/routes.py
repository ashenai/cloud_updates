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

from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, flash, request, jsonify
from sqlalchemy import func, desc, or_
from app.models import Update, WeeklyInsight
from app.scraper.aws_scraper import AWSScraper
from app.scraper.azure_scraper import AzureScraper
from app.scraper.aws_services import AWSServicesFetcher
from app import db

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
        return render_template('index.html')

    @app.route('/aws')
    def aws_updates():
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Number of updates per page
        
        # Get filter parameters from query string
        selected_products = request.args.getlist('products')
        
        # Start with base query
        query = Update.query.filter_by(provider='aws')
        
        # Apply filters if they exist
        if selected_products:
            query = query.filter(Update.product_name.in_(selected_products))
        
        # Get total filtered count before pagination
        total_filtered = query.count()
        
        # Apply sorting and pagination
        pagination = query.order_by(Update.published_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        aws_updates = pagination.items
        
        # Get all unique product names for filtering (from entire dataset)
        aws_products = db.session.query(Update.product_name).filter(
            Update.provider == 'aws',
            Update.product_name.isnot(None)
        ).distinct().all()
        aws_products = sorted([p[0] for p in aws_products if p[0]])  # Flatten and remove empty
        
        return render_template('aws.html', 
                             aws_updates=aws_updates,
                             aws_products=aws_products,
                             selected_products=selected_products,
                             pagination=pagination,
                             total_filtered=total_filtered)

    @app.route('/azure')
    def azure_updates():
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Number of updates per page
        
        # Get filter parameters from query string
        selected_categories = request.args.getlist('categories')
        selected_types = request.args.getlist('types')
        
        # Start with base query
        query = Update.query.filter_by(provider='azure')
        
        # Apply filters if they exist
        if selected_categories:
            # Create conditions for each category
            category_conditions = []
            for category in selected_categories:
                category_conditions.append(Update._categories.like(f'%{category}%'))
            query = query.filter(or_(*category_conditions))
            
        if selected_types:
            # Create conditions for each type
            type_conditions = []
            for update_type in selected_types:
                type_conditions.append(Update._update_types.like(f'%{update_type}%'))
            query = query.filter(or_(*type_conditions))
        
        # Get total filtered count before pagination
        total_filtered = query.count()
        
        # Apply sorting and pagination
        pagination = query.order_by(Update.published_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        azure_updates = pagination.items
        
        # Get all unique categories and types (from entire dataset)
        all_updates = Update.query.filter_by(provider='azure').all()
        azure_categories = set()
        azure_update_types = set()
        
        for update in all_updates:
            if update.categories:
                azure_categories.update(update.categories)
            if update.update_types:
                azure_update_types.update(update.update_types)
        
        return render_template('azure.html', 
                             azure_updates=azure_updates,
                             azure_categories=sorted(azure_categories),
                             azure_update_types=sorted(azure_update_types),
                             selected_categories=selected_categories,
                             selected_types=selected_types,
                             pagination=pagination,
                             total_filtered=total_filtered)

    @app.route('/insights')
    def insights():
        # Get the start of the current week
        today = datetime.utcnow()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

        # AWS Insights
        aws_updates = Update.query.filter(
            Update.provider == 'aws',
            Update.published_date >= start_of_week
        ).all()

        aws_categories = {}
        for update in aws_updates:
            for category in update.categories:
                aws_categories[category] = aws_categories.get(category, 0) + 1

        aws_total = len(aws_updates)
        aws_insights = [
            {
                'category': category,
                'count': count,
                'percentage': (count / aws_total * 100) if aws_total > 0 else 0
            }
            for category, count in sorted(aws_categories.items(), key=lambda x: x[1], reverse=True)
        ]

        # Azure Insights
        azure_updates = Update.query.filter(
            Update.provider == 'azure',
            Update.published_date >= start_of_week
        ).all()

        azure_categories = {}
        for update in azure_updates:
            for category in update.categories:
                azure_categories[category] = azure_categories.get(category, 0) + 1

        azure_total = len(azure_updates)
        azure_insights = [
            {
                'category': category,
                'count': count,
                'percentage': (count / azure_total * 100) if azure_total > 0 else 0
            }
            for category, count in sorted(azure_categories.items(), key=lambda x: x[1], reverse=True)
        ]

        # Weekly Trends
        weekly_trends = []
        for i in range(4):  # Last 4 weeks
            week_start = start_of_week - timedelta(weeks=i)
            week_end = week_start + timedelta(days=7)
            
            aws_count = Update.query.filter(
                Update.provider == 'aws',
                Update.published_date >= week_start,
                Update.published_date < week_end
            ).count()
            
            azure_count = Update.query.filter(
                Update.provider == 'azure',
                Update.published_date >= week_start,
                Update.published_date < week_end
            ).count()
            
            weekly_trends.append({
                'week_start': week_start,
                'aws_count': aws_count,
                'azure_count': azure_count
            })

        return render_template('insights.html',
                            aws_insights=aws_insights,
                            azure_insights=azure_insights,
                            weekly_trends=weekly_trends)

    @app.route('/admin')
    def admin():
        aws_count = Update.query.filter_by(provider='aws').count()
        azure_count = Update.query.filter_by(provider='azure').count()
        latest_update = Update.query.order_by(Update.created_at.desc()).first()
        last_refresh = latest_update.created_at if latest_update else None
        return render_template('admin.html', aws_count=aws_count, azure_count=azure_count, last_refresh=last_refresh)

    @app.route('/admin/refresh', methods=['GET', 'POST'])
    def admin_refresh():
        try:
            # AWS Updates
            aws_scraper = AWSScraper()
            aws_updates = aws_scraper.scrape()
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

            # Azure Updates
            azure_scraper = AzureScraper()
            azure_updates = azure_scraper.scrape()
            for update in azure_updates:
                # Check if update already exists
                existing_update = Update.query.filter_by(
                    provider='azure',
                    title=update.title,
                    published_date=update.published_date
                ).first()
                
                if not existing_update:
                    db.session.add(update)

            db.session.commit()
            flash('Successfully refreshed updates!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving update: {str(e)}', 'error')

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

    @app.route('/debug')
    def debug():
        aws_updates = Update.query.filter_by(provider='aws').order_by(Update.published_date.desc()).limit(3).all()
        azure_updates = Update.query.filter_by(provider='azure').order_by(Update.published_date.desc()).limit(3).all()
        
        aws_count = Update.query.filter_by(provider='aws').count()
        azure_count = Update.query.filter_by(provider='azure').count()
        
        debug_info = {
            'counts': {
                'aws': aws_count,
                'azure': azure_count
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
