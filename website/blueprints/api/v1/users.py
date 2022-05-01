# TODO:

"""
from quart import Blueprint, abort, current_app, g, jsonify, request, session

@blueprint.route("/users")
async def get_users():
    try:
        with psycopg.connect(POSTGRESQL_URI) as connection:
            with connection.cursor() as cursor:
                users_data = dict()
                cursor.execute("SELECT uid, discord FROM users ORDER BY uid;")
                users = cursor.fetchall()
                for user in users:
                    user_uid = user[0]
                    users_data[user_uid] = dict()
                    users_data[user_uid]["discord"] = user[1]
                return jsonify(users_data)
    except Exception as e:
        abort(500, e)
"""