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
        # Get weekly insights ordered by week_start
        insights = WeeklyInsight.query.order_by(WeeklyInsight.week_start.asc()).all()
        
        # Prepare trend chart data
        labels = []
        aws_data = []
        azure_data = []
        
        for insight in insights:
            # Format date as 'YYYY-MM-DD'
            week_label = insight.week_start.strftime('%Y-%m-%d')
            labels.append(week_label)
            aws_data.append(insight.aws_updates)
            azure_data.append(insight.azure_updates)
        
        trend_chart_data = {
            'labels': labels,
            'datasets': [
                {
                    'label': 'AWS Updates',
                    'data': aws_data,
                    'borderColor': '#FF9900',  # AWS brand color
                    'backgroundColor': 'rgba(255, 153, 0, 0.1)',
                    'fill': True
                },
                {
                    'label': 'Azure Updates',
                    'data': azure_data,
                    'borderColor': '#008AD7',  # Azure brand color
                    'backgroundColor': 'rgba(0, 138, 215, 0.1)',
                    'fill': True
                }
            ]
        }
        
        # Get Azure category distribution
        azure_updates = Update.query.filter_by(provider='azure').all()
        azure_categories = {}
        for update in azure_updates:
            for category in update.categories:
                azure_categories[category] = azure_categories.get(category, 0) + 1
        
        # Sort categories by count and get top 5
        sorted_azure_categories = sorted(azure_categories.items(), key=lambda x: x[1], reverse=True)
        top_5_azure = sorted_azure_categories[:5]
        rest_azure = sum(count for _, count in sorted_azure_categories[5:])
        
        azure_chart_data = {
            'labels': [cat[0] for cat in top_5_azure] + ['Rest'],
            'datasets': [{
                'label': 'Azure Updates by Category',
                'data': [cat[1] for cat in top_5_azure] + [rest_azure],
                'backgroundColor': [
                    '#008AD7',  # Azure blue
                    '#00A2ED',
                    '#00B7FF',
                    '#33C6FF',
                    '#66D5FF',
                    '#99E4FF'  # Lighter shade for 'Rest'
                ]
            }]
        }
        
        # Get AWS product distribution
        aws_updates = Update.query.filter_by(provider='aws').all()
        aws_products = {}
        for update in aws_updates:
            if update.product_name:
                aws_products[update.product_name] = aws_products.get(update.product_name, 0) + 1
        
        # Sort products by count and get top 5
        sorted_aws_products = sorted(aws_products.items(), key=lambda x: x[1], reverse=True)
        top_5_aws = sorted_aws_products[:5]
        rest_aws = sum(count for _, count in sorted_aws_products[5:])
        
        aws_chart_data = {
            'labels': [prod[0] for prod in top_5_aws] + ['Rest'],
            'datasets': [{
                'label': 'AWS Updates by Product',
                'data': [prod[1] for prod in top_5_aws] + [rest_aws],
                'backgroundColor': [
                    '#FF9900',  # AWS orange
                    '#FFB13D',
                    '#FFC266',
                    '#FFD699',
                    '#FFE4B3',
                    '#FFF2D9'  # Lighter shade for 'Rest'
                ]
            }]
        }
        
        return render_template('insights.html', 
                             insights=insights,
                             trend_chart_data=trend_chart_data,
                             azure_chart_data=azure_chart_data,
                             aws_chart_data=aws_chart_data)

    @app.route('/admin')
    def admin():
        # Generate weekly insights
        # Start from 4 weeks ago
        today = datetime.utcnow()
        start_of_current_week = today - timedelta(days=today.weekday())
        start_of_current_week = start_of_current_week.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(4):  # Last 4 weeks
            week_start = start_of_current_week - timedelta(weeks=i)
            week_end = week_start + timedelta(days=7)
            
            # Check if insight already exists for this week
            existing_insight = WeeklyInsight.query.filter_by(week_start=week_start).first()
            if existing_insight:
                continue
            
            # Count updates for this week
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
            
            # Create new insight
            insight = WeeklyInsight(
                week_start=week_start,
                week_end=week_end,
                aws_updates=aws_count,
                azure_updates=azure_count
            )
            db.session.add(insight)
        
        try:
            db.session.commit()
            flash('Weekly insights have been generated.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error generating insights: {str(e)}', 'error')
        
        # Get stats for display
        aws_count = Update.query.filter_by(provider='aws').count()
        azure_count = Update.query.filter_by(provider='azure').count()
        latest_update = Update.query.order_by(Update.created_at.desc()).first()
        last_refresh = latest_update.created_at if latest_update else None
        return render_template('admin.html', aws_count=aws_count, azure_count=azure_count, last_refresh=last_refresh)

    @app.route('/admin/refresh', methods=['POST'])
    def admin_refresh():
        # Create scrapers
        aws_scraper = AWSScraper()
        azure_scraper = AzureScraper()
        
        try:
            # Fetch updates
            aws_scraper.fetch_updates()
            azure_scraper.fetch_updates()
            flash('Successfully fetched new updates.', 'success')
        except Exception as e:
            flash(f'Error fetching updates: {str(e)}', 'error')
        
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
