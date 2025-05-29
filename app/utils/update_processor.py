"""Update processor module for cloud updates."""
import re
import json
import os
from datetime import datetime
from app.scraper.aws_services import AWSServicesFetcher

class UpdateProcessor:
    """Process cloud updates to extract metadata."""
    
    def __init__(self):
        # Use the existing AWSServicesFetcher to get services
        self.aws_services_fetcher = AWSServicesFetcher()
        self.aws_services = self.aws_services_fetcher.get_services()
        # Sort by length for better matching (longer names first)
        self.aws_services = sorted(self.aws_services, key=len, reverse=True)
        
        # Azure tag classification lists
        self.azure_status_tags = {
            'In development', 'In preview', 'Launched'
        }
        
        self.azure_update_types = {
            'Compliance', 'Features', 'Gallery', 'Management', 
            'Microsoft Build', 'Microsoft Connect', 'Microsoft Ignite', 
            'Microsoft Inspire', 'MicrosoftBuild', 'Open Source', 
            'Operating System', 'Pricing & Offerings', 
            'Regions & Datacenters', 'Retirements', 'SDK & Tools', 
            'Security', 'Services'
        }

    def extract_aws_product(self, title, description):
        """Robust AWS product extraction using the AWS services list with pattern matching fallback."""
        if not title:
            return None
            
        # Skip generic AWS terms that aren't actual services
        generic_terms = {'account', 'region', 'regions', 'Europe', 'Paris', 'Central', 'US', 'support', 
                        'AWS Cloud', 'AWS services', 'AWS service', 'AWS Region', 'AWS Regions'}
        
        # 1. First, check for exact matches from the services list
        for service in self.aws_services:
            if service in title and service not in generic_terms:
                return service
        
        # 2. Try to extract using regex patterns for "AWS X" or "Amazon Y"
        # This is now a FALLBACK when service isn't in the list
        aws_patterns = [
            r'Amazon\s+([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)',
            r'AWS\s+([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)'
        ]
        
        for pattern in aws_patterns:
            matches = re.findall(pattern, title)
            if matches:
                # Get the longest match
                longest_match = max(matches, key=len)
                candidate = f"{'AWS' if pattern.startswith('AWS') else 'Amazon'} {longest_match}"
                # No longer checking if candidate is in self.aws_services
                if candidate not in generic_terms:
                    return candidate
        
        # 3. Special case for titles with "now supports" or similar phrases
        support_patterns = [
            r'(Amazon\s+[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\s+now\s+',
            r'(AWS\s+[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\s+now\s+'
        ]
        
        for pattern in support_patterns:
            match = re.search(pattern, title)
            if match:
                candidate = match.group(1).strip()
                # No longer checking if candidate is in self.aws_services
                if candidate not in generic_terms:
                    return candidate
          # 4. Check for "is now" pattern which often indicates a product announcement
        # Fixed regex to avoid exponential backtracking by simplifying the pattern
        is_now_pattern = r'((?:Amazon|AWS)\s+[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+){0,5})\s+.*?\bis\s+now'
        match = re.search(is_now_pattern, title)
        if match:
            candidate = match.group(1).strip()
            # Extract just the service name (not feature names)
            service_parts = candidate.split()
            if len(service_parts) > 2:  # More than "Amazon X"
                # Try to find where the service name ends and feature begins
                for i in range(2, len(service_parts)):
                    partial_service = ' '.join(service_parts[:i])
                    if partial_service in self.aws_services:
                        return partial_service
            
            # Check if the full candidate is in our services list
            if candidate in self.aws_services:
                return candidate
            
            # If not in services list, return it anyway as fallback
            return candidate
            
        # If nothing matched, return None
        return None

    def extract_azure_categories(self, entry):
        """Extract categories from Azure update entry.
        
        Note: This method is kept for backward compatibility.
        It now returns all product tags (categories that aren't status or update types).
        """
        return self.extract_azure_products(entry)

    def extract_azure_status(self, entry):
        """Extract status tags from Azure update entry."""
        categories = entry.get('categories', [])
        status_tags = []
        
        # Debug
        print(f"Extracting status from categories: {categories}")
        print(f"Status tags to look for: {self.azure_status_tags}")
        
        for category in categories:
            category = category.strip()
            if category in self.azure_status_tags:
                status_tags.append(category)
                print(f"Found status tag: {category}")
        
        # If no status tags found, default to 'Launched'
        if not status_tags:
            print("No status tags found, defaulting to 'Launched'")
            status_tags = ['Launched']
            
        return list(set(status_tags))

    def extract_azure_types(self, entry):
        """Extract update types from Azure update entry."""
        categories = entry.get('categories', [])
        update_types = []
        
        # Debug
        print(f"Extracting update types from categories: {categories}")
        print(f"Update types to look for: {self.azure_update_types}")
        
        for category in categories:
            category = category.strip()
            if category in self.azure_update_types:
                update_types.append(category)
                print(f"Found update type: {category}")
                
        # If no update types found, default to 'Features'
        if not update_types:
            print("No update types found, defaulting to 'Features'")
            update_types = ['Features']
            
        return list(set(update_types))

    def extract_azure_products(self, entry):
        """Extract product names from Azure update entry.
        
        Products are any category tags that are not status or update types.
        There can be multiple products per update.
        """
        categories = entry.get('categories', [])
        product_tags = []
        
        for category in categories:
            category = category.strip()
            if category and category not in self.azure_status_tags and category not in self.azure_update_types:
                product_tags.append(category)
        
        return list(set(product_tags)) if product_tags else None

    def process_aws_update(self, entry):
        return {
            'product_name': self.extract_aws_product(
                entry.get('title', ''),
                entry.get('description', '')
            ),
            'categories': None,
            'update_types': None
        }

    def process_azure_update(self, entry):
        """Process Azure update entry to extract metadata.
        
        Returns a dictionary with:
        - product_name: Primary product name (first one)
        - product_names: List of product names (categories that aren't status or update types)
        - categories: Same as product_names (kept for backward compatibility)
        - update_types: List of update types
        - status: List of status tags
        """
        products = self.extract_azure_products(entry)
        
        return {
            'product_name': products[0] if products else None,  # Primary product (first one)
            'product_names': products,  # All products
            'categories': products,  # For backward compatibility
            'update_types': self.extract_azure_types(entry),
            'status': self.extract_azure_status(entry)
        }
