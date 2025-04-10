"""
AWS Updates Scraper
"""

import feedparser
from datetime import datetime
import re
from .aws_services import AWSServicesFetcher
from email.utils import parsedate_to_datetime

class AWSScraper:
    def __init__(self):
        self.rss_url = "https://aws.amazon.com/about-aws/whats-new/recent/feed/"
        self._services_fetcher = AWSServicesFetcher()
        self._services = None

    def _get_services(self):
        """Get or load AWS services list."""
        if self._services is None:
            self._services = self._services_fetcher.get_services()
        return self._services

    def extract_product_name(self, title):
        """
        Extract AWS product name from update title by trying four matching patterns:
        1. Full service name (e.g. "Amazon DynamoDB")
        2. AWS prefix + name (e.g. "AWS <name>")
        3. Amazon prefix + name (e.g. "Amazon <name>")
        4. Name only (e.g. "DynamoDB")
        """
        print(f"\nProcessing title: {title}")
        
        # Get our services list and prepare title
        services = self._get_services()
        title_lower = title.lower()
        
        # Special cases for services that might appear differently
        special_cases = {
            'Well-Architected Tool': 'AWS Well-Architected Tool',
            'DynamoDB': 'Amazon DynamoDB',
            'S3 Tables': 'Amazon S3',
            'Cost Optimization Hub': 'AWS Cost Optimization Hub',
            'Resource Access Manager': 'AWS Resource Access Manager',
            'PartyRock': 'Amazon PartyRock',
            'OpenSearch UI': 'Amazon OpenSearch Service',
            'MSK': 'Amazon MSK',
            'API Gateway': 'Amazon API Gateway',
            'IoT': 'AWS IoT',
            'Marketplace': 'AWS Marketplace',
            'End User Messaging': 'AWS End User Computing',
            'EKS': 'Amazon EKS',
            'ECS': 'Amazon ECS',
            'EC2': 'Amazon EC2',
            'RDS': 'Amazon RDS',
            'Lambda': 'AWS Lambda',
            'CloudFront': 'Amazon CloudFront',
            'Route 53': 'Amazon Route 53',
            'VPC': 'Amazon VPC',
            'IAM': 'AWS IAM',
            'CloudWatch': 'Amazon CloudWatch',
            'CloudFormation': 'AWS CloudFormation',
            'SQS': 'Amazon SQS',
            'SNS': 'Amazon SNS',
            'SES': 'Amazon SES',
            'Q Developer': 'Amazon Q',
            'Amazon Q': 'Amazon Q',  # Only match exact "Amazon Q"
            'MQ': 'Amazon MQ',
            'OpenSearch Ingestion': 'Amazon OpenSearch Service',
            'Nova Canvas': 'Amazon Bedrock',
            'Nova Sonic': 'Amazon Bedrock',
            'Aurora PostgreSQL': 'Amazon Aurora',  # Handle Aurora PostgreSQL variant
            'Aurora Postgres': 'Amazon Aurora',    # Handle another common variant
            'Well-Architected': 'AWS Well-Architected Tool',  # Match partial name
            'Well Architected': 'AWS Well-Architected Tool'   # Handle without hyphen
        }
        
        # Check special cases first
        for pattern, service_name in special_cases.items():
            if pattern.lower() in title_lower:
                print(f"Found special case match: {service_name}")
                return service_name
        
        # Try to find the longest matching service name
        max_length = 0
        matched_service = None
        
        for service in services:
            service_lower = service.lower()
            service_name = service.replace('AWS ', '').replace('Amazon ', '')
            service_name_lower = service_name.lower()
            
            # Skip if service name is too short (likely an abbreviation)
            if len(service_name) <= 3:
                continue
            
            # Skip if service name is too generic
            if service_name_lower in {'products', 'services', 'developer', 'tools'}:
                continue
            
            # Try full service name match first (highest priority)
            if service_lower in title_lower:
                length = len(service_lower)
                if length > max_length:
                    max_length = length
                    matched_service = service
                    continue
            
            # Try AWS prefix + name
            aws_pattern = f"aws {service_name_lower}"
            if aws_pattern in title_lower:
                length = len(aws_pattern)
                if length > max_length:
                    max_length = length
                    matched_service = f"AWS {service_name}"
                    continue
            
            # Try Amazon prefix + name
            amazon_pattern = f"amazon {service_name_lower}"
            if amazon_pattern in title_lower:
                length = len(amazon_pattern)
                if length > max_length:
                    max_length = length
                    matched_service = f"Amazon {service_name}"
                    continue
            
            # Try name only for longer names (to avoid false positives)
            # First try the full service name without requiring prefix match
            if len(service_name) > 3:
                # Remove AWS/Amazon prefix if present
                clean_service = service.replace('AWS ', '').replace('Amazon ', '')
                if clean_service.lower() in title_lower:
                    length = len(clean_service)
                    if length > max_length:
                        max_length = length
                        matched_service = service  # Use original service name with prefix
                        continue
                
                # Then try the service name part
                if service_name_lower in title_lower:
                    length = len(service_name_lower)
                    if length > max_length:
                        max_length = length
                        matched_service = service  # Use original service name with prefix
        
        if matched_service:
            print(f"Found service match: {matched_service}")
            return matched_service
        
        print("No product name found")
        return None

    def clean_description(self, description):
        """Clean the HTML description."""
        # For now, just return the raw description
        return description

    def scrape(self):
        """Scrape AWS updates from RSS feed."""
        try:
            feed = feedparser.parse(self.rss_url)
            if not feed.entries:
                print("No AWS entries found in feed")
                return []
                
            updates = []
            categories = []  # AWS doesn't provide categories in RSS
            
            for entry in feed.entries:
                try:
                    # Extract product name
                    product_name = self.extract_product_name(entry.title)
                    
                    # Skip entries without dates
                    if not entry.get('published'):
                        print(f"Warning: AWS entry missing published date: {entry.title}")
                        continue
                        
                    # Parse date using email.utils for RFC822 format
                    published_date = parsedate_to_datetime(entry.published)
                    
                    # Clean description
                    clean_description = self.clean_description(entry.description)
                    
                    # Create update object
                    update = {
                        'provider': 'aws',
                        'title': entry.title,
                        'description': clean_description,
                        'url': entry.get('link', ''),
                        'published_date': published_date,
                        'categories': categories,
                        'product_name': product_name,
                        'update_types': []  # AWS doesn't have explicit update types
                    }
                    updates.append(update)
                except Exception as entry_error:
                    print(f"Error processing AWS entry: {entry_error}")
                    continue
            
            print(f"\nSuccessfully processed {len(updates)} AWS updates")
            return updates
            
        except Exception as e:
            print(f"Error scraping AWS updates: {e}")
            return []

# Example usage
if __name__ == "__main__":
    scraper = AWSScraper()
    updates = scraper.scrape()
    for update in updates:
        print(f"\nTitle: {update['title']}")
        print(f"Product: {update['product_name']}")
        print(f"Date: {update['published_date']}")
        print(f"Link: {update['url']}")
        print("-" * 80)
