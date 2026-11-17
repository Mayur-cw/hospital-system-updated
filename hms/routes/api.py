from datetime import datetime

from flask import Blueprint, jsonify, render_template_string, request
from flask_login import current_user, login_required

from hms.services.availability import AvailabilityService
from hms.services.notifications import NotificationService
from hms.services.search import SearchService

api_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')


@api_bp.route('/doctors/<int:doctor_id>/slots', methods=['GET'])
def get_doctor_slots(doctor_id: int):
    """
    F-03: Real-time appointment availability slot generator.
    Replaces legacy client-side calculations and deprecated POST /get_booked_slots.
    """
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({"error": "Query parameter 'date' (YYYY-MM-DD) is required"}), 400

    try:
        query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Expected YYYY-MM-DD"}), 400

    slots = AvailabilityService.get_available_slots(doctor_id, query_date)
    return jsonify({
        "doctor_id": doctor_id,
        "date": query_date.isoformat(),
        "total_slots": len(slots),
        "available_slots": [s for s in slots if s['available']],
        "slots": slots
    }), 200


@api_bp.route('/search', methods=['GET'])
def global_search():
    """
    F-02: Global typeahead search endpoint.
    Authorization-scoped by current session role.
    """
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all').strip()

    if not query:
        return jsonify({"results": []}), 200

    results = SearchService.global_search(query, current_user=current_user, search_type=search_type)
    return jsonify({
        "query": query,
        "count": len(results),
        "results": results
    }), 200


@api_bp.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    """
    F-05: In-app notification center feed.
    """
    unread = NotificationService.get_unread_notifications(current_user.id)
    return jsonify({
        "unread_count": len(unread),
        "notifications": [n.to_dict() for n in unread[:20]]
    }), 200


@api_bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id: int):
    """
    F-05: Mark notification as read.
    """
    success = NotificationService.mark_notification_as_read(notif_id, current_user.id)
    if success:
        return jsonify({"status": "success", "id": notif_id}), 200
    return jsonify({"error": "Notification not found"}), 404


@api_bp.route('/openapi.json', methods=['GET'])
def openapi_spec():
    """
    F-11: OpenAPI 3.0 specification for Hedgewar Hospital Care v1 API.
    """
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "Hedgewar Hospital Care API",
            "version": "1.0.0",
            "description": "Standardized RESTful API for clinical scheduling, availability, typeahead search, and in-app notifications."
        },
        "servers": [{"url": "/api/v1"}],
        "paths": {
            "/doctors/{doctor_id}/slots": {
                "get": {
                    "summary": "Retrieve available appointment slots for a doctor on a specific date",
                    "parameters": [
                        {"name": "doctor_id", "in": "path", "required": True, "schema": {"type": "integer"}},
                        {"name": "date", "in": "query", "required": True, "schema": {"type": "string", "format": "date"}}
                    ],
                    "responses": {
                        "200": {"description": "List of slots for the given date"},
                        "400": {"description": "Invalid date parameter"}
                    }
                }
            },
            "/search": {
                "get": {
                    "summary": "Global search across physicians, clinical specialties, and patients",
                    "parameters": [
                        {"name": "q", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "type", "in": "query", "required": False, "schema": {"type": "string", "enum": ["all", "doctors", "patients"]}}
                    ],
                    "responses": {
                        "200": {"description": "Array of search results matching the query and role scope"}
                    }
                }
            },
            "/notifications": {
                "get": {
                    "summary": "Get unread in-app notifications for authenticated user",
                    "responses": {
                        "200": {"description": "Unread count and list of notifications"},
                        "401": {"description": "Authentication required"}
                    }
                }
            }
        }
    }
    return jsonify(spec), 200


@api_bp.route('/docs', methods=['GET'])
def api_docs():
    """
    F-11: Self-hosted Swagger UI / API documentation viewer.
    """
    docs_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8"/>
      <title>API Documentation | Hedgewar Hospital Care</title>
      <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css"/>
      <link rel="icon" type="image/svg+xml" href="/static/images/favicon.svg"/>
    </head>
    <body style="margin: 0; padding: 0;">
      <div id="swagger-ui"></div>
      <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js"></script>
      <script>
        window.onload = function() {
          SwaggerUIBundle({
            url: "/api/v1/openapi.json",
            dom_id: '#swagger-ui',
            presets: [SwaggerUIBundle.presets.apis],
            layout: "BaseLayout"
          });
        };
      </script>
    </body>
    </html>
    """
    return render_template_string(docs_html)
