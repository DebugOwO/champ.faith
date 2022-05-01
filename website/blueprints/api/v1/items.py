# TODO:

"""
from quart import Blueprint, abort, current_app, g, jsonify, request, session

@blueprint.route("/data")
async def get_items_data():
    try:
        with psycopg.connect(POSTGRESQL_URI) as connection:
            with connection.cursor() as cursor:
                sorting_index = ["knifes", "chairs", "accessories"]
                items_data = dict()
                for sorting in sorting_index:
                    cursor.execute(
                        f"SELECT id, name, price, stock FROM items.{sorting} ORDER BY id;"
                    )
                    items = cursor.fetchall()
                    data = dict()
                    for item in items:
                        item_id = item[0]
                        data[item_id] = dict()
                        (
                            data[item_id]["name"],
                            data[item_id]["price"],
                            data[item_id]["stock"],
                        ) = (item[1], item[2], item[3])
                    items_data[sorting] = data
                return jsonify(items_data)
    except Exception as e:
        abort(500, e)


@blueprint.route("/update")
async def update_item():
    try:

        def data_dict(item_list):
            data = dict()
            for item in item_list:
                item_id = item[0]
                data[item_id] = dict()
                (
                    data[item_id]["name"],
                    data[item_id]["price"],
                    data[item_id]["stock"],
                ) = (item[1], item[2], item[3])
            return data

        with psycopg.connect(POSTGRESQL_URI) as connection:
            with connection.cursor() as cursor:
                sorting_index = ["knifes", "chairs", "accessories"]
                items_data = dict()
                for sorting in sorting_index:
                    cursor.execute(
                        f"SELECT id, name, price, stock FROM items.{sorting} ORDER BY id;"
                    )
                    items = cursor.fetchall()
                    items_data[sorting] = data_dict(items)
                return jsonify(items_data)
    except Exception as e:
        abort(500, e)
"""
