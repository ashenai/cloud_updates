from flask import render_template, jsonify, current_app
from app import db
from app.models import Update, WeeklyInsight
from app.scraper.aws_scraper import AWSScraper
from app.scraper.azure_scraper import AzureScraper
import schedule
import time
from datetime import datetime, timedelta
import re

def init_routes(app):
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}

    @app.route('/')
    def index():
        aws_updates = Update.query.filter_by(provider='aws').order_by(Update.published_date.desc()).limit(20).all()
        azure_updates = Update.query.filter_by(provider='azure').order_by(Update.published_date.desc()).limit(20).all()
        return render_template('index.html', aws_updates=aws_updates, azure_updates=azure_updates)

    def extract_service_name(title, provider):
        if provider == 'aws':
            # Common AWS service patterns
            patterns = [
                r'Amazon ([\w\s]+)',
                r'AWS ([\w\s]+)',
                r'Amazon Web Services ([\w\s]+)'
            ]
            for pattern in patterns:
                match = re.search(pattern, title)
                if match:
                    return match.group(1).strip()
            return 'Other AWS Services'
        else:
            # Common Azure service patterns
            patterns = [
                r'Azure ([\w\s]+)',
                r'Microsoft ([\w\s]+) Azure'
            ]
            for pattern in patterns:
                match = re.search(pattern, title)
                if match:
                    return match.group(1).strip()
            return 'Other Azure Services'

    @app.route('/insights')
    def insights():
        # Get current week's updates
        now = datetime.utcnow()
        start_of_week = now - timedelta(days=now.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        # Get all updates from this week
        aws_updates = Update.query.filter(
            Update.provider == 'aws',
            Update.published_date >= start_of_week,
            Update.published_date <= end_of_week
        ).all()

        azure_updates = Update.query.filter(
            Update.provider == 'azure',
            Update.published_date >= start_of_week,
            Update.published_date <= end_of_week
        ).all()

        # Group updates by service
        aws_services = {}
        azure_services = {}

        for update in aws_updates:
            service = extract_service_name(update.title, 'aws')
            if service not in aws_services:
                aws_services[service] = []
            aws_services[service].append(update)

        for update in azure_updates:
            service = extract_service_name(update.title, 'azure')
            if service not in azure_services:
                azure_services[service] = []
            azure_services[service].append(update)

        # Get historical insights
        historical_insights = WeeklyInsight.query.order_by(WeeklyInsight.week_start.desc()).all()

        return render_template('insights.html', 
                            aws_services=aws_services,
                            azure_services=azure_services,
                            historical_insights=historical_insights,
                            week_start=start_of_week,
                            week_end=end_of_week)

    @app.route('/debug')
    def debug():
        aws_count = Update.query.filter_by(provider='aws').count()
        azure_count = Update.query.filter_by(provider='azure').count()
        
        # Get sample updates
        aws_updates = Update.query.filter_by(provider='aws').limit(3).all()
        azure_updates = Update.query.filter_by(provider='azure').limit(3).all()
        
        debug_info = {
            'counts': {
                'aws': aws_count,
                'azure': azure_count
            },
            'sample_aws': [{'title': u.title, 'provider': u.provider, 'date': u.published_date.isoformat()} for u in aws_updates],
            'sample_azure': [{'title': u.title, 'provider': u.provider, 'date': u.published_date.isoformat()} for u in azure_updates]
        }
        return jsonify(debug_info)

    def scrape_updates():
        print("Fetching updates from AWS and Azure...")
        with app.app_context():
            try:
                aws_scraper = AWSScraper()
                azure_scraper = AzureScraper()
                
                aws_updates = aws_scraper.scrape()
                azure_updates = azure_scraper.scrape()
                
                print(f"Found {len(aws_updates)} AWS updates and {len(azure_updates)} Azure updates")
                
                # Save updates to database
                new_updates = 0
                for update in aws_updates + azure_updates:
                    try:
                        db.session.add(update)
                        db.session.commit()
                        new_updates += 1
                    except Exception as e:
                        # Rollback the failed transaction
                        db.session.rollback()
                        if 'unique_update' in str(e):
                            # Skip duplicates silently
                            continue
                        else:
                            # Log other errors
                            print(f"Error saving update: {e}")
                
                print(f"Added {new_updates} new updates to database")
                
                # Generate weekly insights
                generate_weekly_insights()
            except Exception as e:
                print(f"Error during scraping: {e}")
                db.session.rollback()

    def generate_weekly_insights():
        with app.app_context():
            # Get current week's updates
            now = datetime.utcnow()
            start_of_week = now - timedelta(days=now.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            
            aws_count = Update.query.filter(
                Update.provider == 'aws',
                Update.published_date >= start_of_week,
                Update.published_date <= end_of_week
            ).count()
            
            azure_count = Update.query.filter(
                Update.provider == 'azure',
                Update.published_date >= start_of_week,
                Update.published_date <= end_of_week
            ).count()
            
            # Create summary
            summary = f"This week had {aws_count} AWS updates and {azure_count} Azure updates."
            
            insight = WeeklyInsight(
                week_start=start_of_week,
                week_end=end_of_week,
                aws_updates=aws_count,
                azure_updates=azure_count,
                summary=summary
            )
            db.session.add(insight)
            db.session.commit()

    # Schedule the scraper to run daily
    schedule.every().day.at("09:00").do(scrape_updates)
    
    # Do an initial scrape
    scrape_updates()

    return schedule
