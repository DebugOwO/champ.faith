import os

from website import create_app

if os.name != "nt":
    import uvloop

    uvloop.install()

debug = True
application = create_app(debug=debug)
