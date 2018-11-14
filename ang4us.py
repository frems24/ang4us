from app import create_app, db
from app.models import User, Post, Fishery, Fish

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Post': Post, 'Fishery': Fishery, 'Fish': Fish}


if __name__ == '__main__':
    print("PyCharm Debugger")
    app.run(debug=True, use_debugger=False, use_reloader=False, passthrough_errors=True)
