"""
Module to fetch and maintain a list of AWS services.
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from pathlib import Path

class AWSServicesFetcher:
    def __init__(self):
        self.docs_overview_url = "https://aws.amazon.com/documentation-overview/"
        self.cache_file = Path(__file__).parent / "aws_services_cache.json"
        self._services = None

    def fetch_services(self):
        """Fetch AWS services from the documentation overview page."""
        try:
            response = requests.get(self.docs_overview_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            services = set()
            
            # Find all service headings and links
            for element in soup.find_all(['h2', 'h3', 'a']):
                text = element.get_text().strip()
                
                # Skip empty or non-service text
                if not text or any(skip in text.lower() for skip in [
                    'documentation', 'guide', 'sdk', 'tools', 'overview',
                    'getting started', 'learn', 'resources', 'developer',
                    'sign in', 'sign out', 'home', 'index', 'console',
                    'support', 'partner', 'training', 'careers', 'marketplace',
                    'privacy', 'terms', 'contact', 'help', 'blog', 'press',
                    'legal', 'cookie', 'preference', 'account', 'profile',
                    'billing', 'cost', 'pricing', 'free', 'trial', 'login',
                    'logout', 'language', 'español', 'português', 'deutsch',
                    'français', 'italiano', 'about', 'what is', 'solutions',
                    'events', 'news', 'mobile', 'download', 'close', 'skip',
                    'expert', 'success', 'enable', 'create', 'got it',
                    'türkçe', 'bahasa', 'english', 'on aws', 'what\'s new'
                ]):
                    continue
                
                # Skip if text contains parentheses or special characters
                if '(' in text or ')' in text or '?' in text or '=' in text:
                    continue
                
                # Skip if text is just an abbreviation (2-3 letters)
                if len(text.replace('AWS ', '').replace('Amazon ', '').strip()) <= 3:
                    continue
                
                # Skip if text contains certain patterns
                if any(pattern in text for pattern in ['& ', '.NET', 'Java', 'Python', 'PHP', 'JavaScript']):
                    continue
                
                # Clean up the service name
                text = re.sub(r'\s+', ' ', text)
                
                # Add AWS/Amazon prefix if missing
                if not text.startswith(('AWS ', 'Amazon ')):
                    if any(word in text.lower() for word in ['cloud', 'elastic', 'service', 'resource', 'cost']):
                        text = f"AWS {text}"
                    else:
                        text = f"Amazon {text}"
                
                services.add(text)
            
            # Add common services that might not be in the docs
            additional_services = {
                'AWS Well-Architected Tool',
                'Amazon DynamoDB',
                'Amazon S3',
                'AWS Cost Optimization Hub',
                'AWS Resource Access Manager',
                'Amazon PartyRock',
                'Amazon OpenSearch Service',
                'Amazon MSK',
                'Amazon EKS',
                'Amazon ECS',
                'Amazon EC2',
                'Amazon RDS',
                'AWS Lambda',
                'Amazon API Gateway',
                'AWS Direct Connect',
                'Amazon CloudFront',
                'Amazon Route 53',
                'Amazon VPC',
                'AWS IAM',
                'Amazon CloudWatch',
                'AWS CloudFormation',
                'Amazon SQS',
                'Amazon SNS',
                'Amazon SES',
                'Amazon Aurora',
                'Amazon Aurora PostgreSQL',
                'Aurora',
                'Aurora PostgreSQL',
                'AWS Step Functions',
                'Amazon EventBridge',
                'AWS CodeBuild',
                'AWS CodePipeline',
                'AWS CodeDeploy',
                'Amazon ECR',
                'AWS Fargate',
                'Amazon DocumentDB',
                'Amazon Neptune',
                'Amazon Redshift',
                'Amazon ElastiCache',
                'Amazon Elasticsearch Service',
                'Amazon Kinesis',
                'AWS Glue',
                'Amazon Athena',
                'Amazon QuickSight',
                'Amazon Managed Blockchain',
                'Amazon QLDB',
                'Amazon Timestream',
                'AWS IoT Core',
                'Amazon SageMaker',
                'Amazon Comprehend',
                'Amazon Rekognition',
                'Amazon Polly',
                'Amazon Lex',
                'Amazon Textract',
                'Amazon Translate',
                'Amazon Transcribe',
                'AWS DeepRacer',
                'AWS DeepLens',
                'Amazon Kendra',
                'Amazon Personalize',
                'Amazon Forecast',
                'Amazon Detective',
                'Amazon GuardDuty',
                'AWS Shield',
                'AWS WAF',
                'Amazon Macie',
                'AWS Security Hub',
                'AWS Secrets Manager',
                'AWS Certificate Manager',
                'AWS Systems Manager',
                'AWS Config',
                'AWS Control Tower',
                'AWS Organizations',
                'AWS Service Catalog',
                'AWS License Manager',
                'AWS Backup',
                'AWS Outposts',
                'AWS Wavelength',
                'AWS Local Zones',
                'AWS Snow Family',
                'AWS Migration Hub',
                'AWS Application Migration Service',
                'AWS Database Migration Service',
                'AWS DataSync',
                'AWS Transfer Family',
                'Amazon WorkSpaces',
                'Amazon AppStream 2.0',
                'Amazon WorkDocs',
                'Amazon Chime',
                'Amazon Connect',
                'Amazon Pinpoint',
                'Amazon Simple Email Service',
                'Amazon Honeycode',
                'AWS Amplify',
                'AWS AppSync',
                'AWS Device Farm',
                'Amazon Location Service',
                'Amazon Managed Blockchain',
                'Amazon Quantum Ledger Database',
                'Amazon Managed Streaming for Apache Kafka',
                'Amazon Managed Streaming for Kafka Connect',
                'Amazon Managed Service for Prometheus',
                'Amazon Managed Grafana',
                'Amazon MemoryDB for Redis',
                'Amazon OpenSearch Serverless',
                'Amazon CodeWhisperer',
                'Amazon Q',
                'Amazon Bedrock'
            }
            
            services.update(additional_services)
            
            # Add variations
            variations = set()
            for service in services:
                # Add version without AWS/Amazon prefix
                base_name = service.replace('AWS ', '').replace('Amazon ', '')
                variations.add(base_name)
                
                # Add common abbreviations
                words = service.split()
                if len(words) > 2:
                    if words[0] in ('AWS', 'Amazon'):
                        abbrev = f"{words[0]} {''.join(word[0] for word in words[1:])}"
                        variations.add(abbrev)
                
                # Add common alternative names
                lower_service = service.lower()
                if "simple storage service" in lower_service:
                    variations.add("Amazon S3")
                    variations.add("S3")
                elif "elastic compute cloud" in lower_service:
                    variations.add("Amazon EC2")
                    variations.add("EC2")
                elif "relational database service" in lower_service:
                    variations.add("Amazon RDS")
                    variations.add("RDS")
                elif "elastic container service" in lower_service:
                    variations.add("Amazon ECS")
                    variations.add("ECS")
                elif "elastic kubernetes service" in lower_service:
                    variations.add("Amazon EKS")
                    variations.add("EKS")
                elif "cloudfront" in lower_service:
                    variations.add("Amazon CloudFront")
                    variations.add("CloudFront")
                elif "dynamodb" in lower_service:
                    variations.add("Amazon DynamoDB")
                    variations.add("DynamoDB")
                elif "lambda" in lower_service:
                    variations.add("AWS Lambda")
                    variations.add("Lambda")
            
            services.update(variations)
            
            # Sort and save to cache
            self._services = sorted(list(services))
            self._save_cache()
            
            return self._services
            
        except Exception as e:
            print(f"Error fetching AWS services: {e}")
            return self._load_cache()  # Fallback to cache

    def _save_cache(self):
        """Save services to cache file."""
        if self._services:
            try:
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self._services, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Error saving cache: {e}")

    def _load_cache(self):
        """Load services from cache file."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
        return []

    def get_services(self, refresh=False):
        """Get AWS services, optionally refreshing the list."""
        if refresh or self._services is None:
            return self.fetch_services()
        return self._services

# Example usage
if __name__ == "__main__":
    fetcher = AWSServicesFetcher()
    services = fetcher.get_services(refresh=True)
    print("\nAWS Services:")
    for service in sorted(services):
        try:
            print(f"- {service}")
        except UnicodeEncodeError:
            # Skip services with non-ASCII characters
            continue
