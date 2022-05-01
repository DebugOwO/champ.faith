# TODO:

"""
from quart import Blueprint, abort, current_app, g, jsonify, request, session

@blueprint.route("/generate")
async def generate_key():
    try:
        with psycopg.connect(POSTGRESQL_URI) as connection:
            with connection.cursor() as cursor:
                api_key = uuid.uuid4()
                cursor.execute(f"INSERT INTO api.keys (uuid) VALUES ({uuid});")
                return jsonify(api_key)
    except Exception as e:
        abort(500, e)
"""