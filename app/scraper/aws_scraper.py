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

from datetime import datetime
from typing import List, Tuple
import feedparser
from bs4 import BeautifulSoup
import re
from app.models import Update
from time import mktime

class AWSScraper:
    def __init__(self):
        self.feed_url = "https://aws.amazon.com/about-aws/whats-new/recent/feed/"
        # Common AWS/Amazon service names
        self.service_patterns = [
            r'AWS Lambda',
            r'AWS Step Functions',
            r'Amazon S3',
            r'Amazon Simple Storage Service',
            r'AWS EC2',
            r'Amazon Elastic Compute Cloud',
            r'Amazon ECS',
            r'Amazon Elastic Container Service',
            r'AWS EKS',
            r'Amazon Elastic Kubernetes Service',
            r'Amazon RDS',
            r'Amazon Relational Database Service',
            r'Amazon DynamoDB',
            r'Amazon Aurora',
            r'AWS CloudFormation',
            r'AWS CloudWatch',
            r'Amazon CloudFront',
            r'AWS IAM',
            r'AWS Identity and Access Management',
            r'Amazon VPC',
            r'Amazon Virtual Private Cloud',
            r'Amazon Route 53',
            r'AWS Systems Manager',
            r'Amazon SQS',
            r'Amazon Simple Queue Service',
            r'Amazon SNS',
            r'Amazon Simple Notification Service',
            r'AWS CodeBuild',
            r'AWS CodePipeline',
            r'AWS CodeDeploy',
            r'Amazon EMR',
            r'Amazon Elastic MapReduce',
            r'Amazon Redshift',
            r'Amazon Athena',
            r'Amazon QuickSight',
            r'AWS Glue',
            r'Amazon Kinesis',
            r'Amazon API Gateway',
            r'AWS AppSync',
            r'Amazon Cognito',
            r'AWS Amplify',
            r'Amazon SageMaker',
            r'Amazon Comprehend',
            r'Amazon Rekognition',
            r'Amazon Textract',
            r'Amazon Polly',
            r'Amazon Lex',
            r'AWS Elemental MediaLive',
            r'AWS Elemental MediaConvert',
            r'AWS Elemental MediaPackage',
            r'AWS Elemental MediaStore',
            r'AWS Elemental MediaTailor',
            r'Amazon OpenSearch Service',
            r'Amazon Elasticsearch Service',
            r'AWS Lake Formation',
            r'AWS Control Tower',
            r'AWS Organizations',
            r'AWS Direct Connect',
            r'Amazon EventBridge',
            r'Amazon CloudWatch Events',
            r'AWS Secrets Manager',
            r'AWS Key Management Service',
            r'AWS KMS',
            r'Amazon EFS',
            r'Amazon Elastic File System',
            r'Amazon FSx',
            r'AWS Fargate',
            r'Amazon ECR',
            r'Amazon Elastic Container Registry',
            r'AWS App Runner',
            r'AWS Batch',
            r'Amazon MQ',
            r'Amazon MSK',
            r'Amazon Managed Streaming for Apache Kafka',
            r'AWS IoT Core',
            r'Amazon Connect',
            r'Amazon WorkSpaces',
            r'Amazon AppStream',
            r'AWS Shield',
            r'AWS WAF',
            r'AWS Backup',
            r'AWS Snow Family',
            r'AWS Snowball',
            r'AWS Snowcone',
            r'AWS Snowmobile',
            r'Amazon Braket',
            r'AWS Ground Station',
            r'Amazon Timestream',
            r'Amazon QLDB',
            r'Amazon Managed Blockchain',
            r'AWS Outposts',
            r'AWS Wavelength',
            r'AWS Local Zones'
        ]
    
    def extract_product_name(self, title):
        """Extract AWS/Amazon product name from the title using known service names."""
        # Try to find any known AWS service in the title
        for pattern in self.service_patterns:
            if pattern in title:
                return pattern
        
        # If no exact match found, try to find AWS/Amazon followed by capitalized words
        # This is a fallback for new or uncommon services
        basic_patterns = [
            r'\b(AWS\s+[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)',
            r'\b(Amazon\s+[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)'
        ]
        
        for pattern in basic_patterns:
            match = re.search(pattern, title)
            if match:
                # Verify it's not just part of a longer phrase
                product_name = match.group(1).strip()
                # Only use if it's relatively short (likely a service name)
                if len(product_name.split()) <= 4:
                    return product_name
        
        return None

    def clean_description(self, description):
        """Clean HTML from description and return plain text."""
        if not description:
            return ""
        
        # Parse HTML and get text
        soup = BeautifulSoup(description, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def scrape(self) -> List[Update]:
        """Scrape AWS updates from RSS feed."""
        try:
            print(f"Fetching AWS feed from {self.feed_url}")
            feed = feedparser.parse(self.feed_url)
            
            if hasattr(feed, 'status') and feed.status != 200:
                print(f"Error: AWS feed returned status {feed.status}")
                return []
                
            if not hasattr(feed, 'entries'):
                print("Error: AWS feed has no entries")
                return []
                
            print(f"Found {len(feed.entries)} AWS updates")
            
            updates = []
            for entry in feed.entries:
                try:
                    # Extract product name as category
                    product_name = self.extract_product_name(entry.title)
                    # Print for debugging
                    print(f"\nProcessing: {entry.title}")
                    print(f"Extracted product name: {product_name}")
                    categories = [product_name] if product_name else []
                    
                    # Convert the time struct to datetime
                    if not hasattr(entry, 'published_parsed'):
                        print(f"Warning: AWS entry missing published date: {entry.title}")
                        continue
                        
                    published_date = datetime.fromtimestamp(mktime(entry.published_parsed))
                    
                    # Clean description
                    clean_description = self.clean_description(entry.description)
                    
                    # Create update object
                    update = Update(
                        provider='aws',
                        title=entry.title,
                        description=clean_description,
                        url=entry.get('link', ''),
                        published_date=published_date,
                        categories=categories,
                        update_types=[]  # AWS doesn't have explicit update types
                    )
                    updates.append(update)
                except Exception as entry_error:
                    print(f"Error processing AWS entry: {entry_error}")
                    continue
            
            print(f"Successfully processed {len(updates)} AWS updates")
            return updates
            
        except Exception as e:
            print(f"Error scraping AWS updates: {e}")
            return []
