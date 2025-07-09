from flask import Blueprint, json, request, jsonify, render_template
from app.extensions import insert_database, fetch_database
from pprint import pprint
from datetime import datetime

# Define how many items per page
ITEMS_PER_PAGE = 10


webhook = Blueprint('Webhook', __name__, url_prefix='/webhook', template_folder='../templates')


@webhook.route('/receiver', methods=["POST"])
def receiver():
    if request.headers.get('Content-Type') == "application/json":
        data = request.get_json()
        if not data:
            return jsonify({"error": "Empty or invalid JSON"}), 400

        event_type = request.headers.get('X-GitHub-Event')
        result = ""
        commit_id = None
        if event_type == "push":
            type_event = "PUSH"
            author = data.get('pusher', {}).get('name', 'unknown')
            to_branch = data.get('ref', '').split('/')[-1]
            from_branch = to_branch
            timestamp = datetime.utcnow().strftime('%d %B %Y - %I:%M %p UTC')
            result = f'"{author}" pushed to "{to_branch}" on {timestamp}'
            
            head_commit = data.get('head_commit', {})
            commit_id = head_commit.get('id', 'unknown')

        elif event_type == "pull_request":
            type_event = "PULL_REQUEST"
            action = data.get('action')
            pr = data.get('pull_request', {})
            author = pr.get('user', {}).get('login', 'unknown')
            from_branch = pr.get('head', {}).get('ref', 'unknown')
            to_branch = pr.get('base', {}).get('ref', 'unknown')
            timestamp = datetime.utcnow().strftime('%d %B %Y - %I:%M %p UTC')

            if action in ['opened', 'synchronize', 'reopened']:
                result = f'"{author}" submitted a pull request from "{from_branch}" to "{to_branch}" on {timestamp}'
            elif action == "closed" and pr.get('merged'):
                type_event = "MERGE"
                result = f'"{author}" merged branch "{from_branch}" to "{to_branch}" on {timestamp}'
            
            head_commit = pr.get('head', {}).get('sha', 'unknown')
            commit_id = head_commit  # This is the commit SHA for the head of the PR

                
        db_result = insert_database(type_event, commit_id, author, from_branch, to_branch, timestamp)
        print(db_result)
        if "message" in db_result:
            return jsonify(db_result), 200
        else:
            return jsonify(db_result), 409

    else:
        return jsonify({"error": "Invalid content type, expected application/json"}), 400


@webhook.route('/logger', methods=["GET"])
def logger():
    try:
        # Get the current page number, default to 1 if not provided
        page = request.args.get('page', 1, type=int)
        print(f"Requested Page: {page}")

        # Calculate the total number of commits for pagination
        total_commits = len(fetch_database(0, 0))
        print(f"Total Commits: {total_commits}")

        total_pages = total_commits // ITEMS_PER_PAGE + (1 if total_commits % ITEMS_PER_PAGE > 0 else 0)
        print(f"Total Pages: {total_pages}")

        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages

        start_row = (page - 1) * ITEMS_PER_PAGE
        stop_row = page * ITEMS_PER_PAGE

        # Fetch logs from the database for the current page
        logs_on_page = fetch_database(start_row, stop_row)
        print(f"Logs on Current Page: {logs_on_page}")

        if not logs_on_page:
            print("No logs available for this page")

        start_commit_no = (page - 1) * ITEMS_PER_PAGE + 1

        # Convert the ObjectId to string and populate the message field
        for log in logs_on_page:
            log['_id'] = str(log['_id'])  # Convert ObjectId to string
            log['commit_no'] = start_commit_no
            log['message'] = (
                f"{log['author']} pushed to <i>{log['to_branch']}</i> on {log['timestamp']}"
                if log['action'] == 'PUSH' else
                f"{log['author']} submitted a pull request from <i>{log['from_branch']}</i> to <i>{log['to_branch']}</i> on {log['timestamp']}"
                if log['action'] == 'PULL_REQUEST' else
                f"{log['author']} merged branch <i>{log['from_branch']}</i> to <i>{log['to_branch']}</i> on {log['timestamp']}"
            )
            start_commit_no += 1

        # Check if the request is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(logs=logs_on_page, page=page, total_pages=total_pages)

        return render_template('logger.html', logs=logs_on_page, page=page, total_pages=total_pages)

    except Exception as e:
        print(f"Error occurred: {e}")  # Catch errors and print them
        return "Internal Server Error", 500
