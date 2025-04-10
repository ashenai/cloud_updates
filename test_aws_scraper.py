from app.scraper.aws_scraper import AWSScraper

def test_product_name_extraction():
    scraper = AWSScraper()
    
    # Test case 1: Amazon Lex
    title1 = "Amazon Lex adds ability to control intent switching during conversations"
    product1 = scraper.extract_product_name(title1)
    print(f"Test 1 - Title: {title1}")
    print(f"Product: {product1}")
    print()
    
    # Test case 2: Amazon RDS
    title2 = "Amazon RDS for SQL Server supports new minor versions for SQL Server 2019 and 2022"
    product2 = scraper.extract_product_name(title2)
    print(f"Test 2 - Title: {title2}")
    print(f"Product: {product2}")

if __name__ == '__main__':
    test_product_name_extraction()
