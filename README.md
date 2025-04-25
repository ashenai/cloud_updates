# Cloud Updates

A Flask web application that monitors and provides insights on the latest updates from AWS and Azure using their RSS feeds.

## ⚠️ AI-Generated Code Notice

This code was generated using artificial intelligence. While efforts have been made to ensure its accuracy and functionality, users should:
1. Review and test the code thoroughly before deployment
2. Be aware that AI-generated code may contain unexpected behaviors
3. Use this code at their own risk
4. Not rely on this code for critical systems without proper validation

## Features

- Real-time monitoring of AWS and Azure service updates
- Organized display of updates in a tabbed interface
- Service-based grouping of updates
- Weekly insights generation
- Historical tracking of update patterns

## Technologies Used

- Python 3.13+
- Flask 3.0.0
- SQLAlchemy
- Bootstrap 5
- RSS Feed Integration

## Installation

1. Clone the repository:
```bash
git clone <your-repository-url>
cd cloud_updates
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Initialize the Database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

5. Run the application:
```bash
python run.py
```

The application will be available at `http://localhost:5000`

## Usage

- **Home Page**: View the latest updates from AWS and Azure in a tabbed interface
- **Insights Page**: See updates grouped by service and historical weekly insights
- Updates are automatically fetched daily at 9:00 AM

## Project Structure

```
cloud_updates/
│
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   ├── scraper/
│   │   ├── aws_scraper.py
│   │   └── azure_scraper.py
│   └── templates/
│       ├── base.html
│       ├── index.html
│       └── insights.html
│
├── instance/
├── venv/
├── .gitignore
├── README.md
├── requirements.txt
└── run.py
```

## License

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

## Contributing

Feel free to submit issues and enhancement requests!
