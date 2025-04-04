from app import create_app, db
import threading
import time

app = create_app()

def run_scheduler():
    while True:
        app.scheduler.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    # Run the Flask application
    app.run(debug=True)
