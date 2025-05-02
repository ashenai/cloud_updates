import pytest
from app.scraper.aws_scraper import AWSScraper
from app.utils.update_processor import UpdateProcessor

def test_product_name_extraction():
    scraper = AWSScraper()
    
    test_cases = [
        {
            "title": "Amazon Lex adds ability to control intent switching during conversations",
            "description": "Amazon Lex now allows developers to control when users can switch intents during conversations.",
            "expected_product": "Amazon Lex"
        },
        {
            "title": "Amazon RDS for SQL Server supports new minor versions for SQL Server 2019 and 2022",
            "description": "Amazon RDS for SQL Server now supports SQL Server 2019 and 2022 minor versions.",
            "expected_product": "Amazon RDS"
        },
        {
            "title": "AWS Lambda now supports up to 10 GB of ephemeral storage",
            "description": "AWS Lambda functions can now use up to 10 GB of ephemeral storage.",
            "expected_product": "AWS Lambda"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        metadata = scraper.processor.process_aws_update({
            'title': case['title'],
            'description': case['description']
        })
        
        print(f"\nTest {i}:")
        print(f"Title: {case['title']}")
        print(f"Expected Product: {case['expected_product']}")
        print(f"Extracted Product: {metadata['product_name']}")
        
        assert metadata['product_name'] == case['expected_product'], \
            f"Expected {case['expected_product']}, but got {metadata['product_name']}"

def test_html_cleaning():
    scraper = AWSScraper()
    html = """
    <div>
        <h1>AWS News</h1>
        <p>Amazon EC2 announces new instance types.</p>
        <script>alert('test');</script>
        <ul>
            <li>Feature 1</li>
            <li>Feature 2</li>
        </ul>
        <p>Learn more about AWS services here.</p>
    </div>
    """
    cleaned = scraper.clean_html(html)
    assert "script" not in cleaned
    assert "Feature 1" not in cleaned  # Lists should be removed
    assert "AWS News" in cleaned
    assert "Learn more about AWS" not in cleaned  # Boilerplate should be removed

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
