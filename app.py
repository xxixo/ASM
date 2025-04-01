from flask import Flask, render_template, request, redirect, url_for, flash
from wtforms import Form, StringField, SelectField, validators
import redis


app = Flask(__name__)
app.secret_key = 'your_secret_key'

redis_host = 'localhost'
redis_port = 6379
redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

class RedisConfigForm(Form):
    host = StringField('Redis Host', [validators.DataRequired()])
    port = StringField('Redis Port', [validators.DataRequired()])


@app.route('/')
def index():
    return render_template('/home/index.html', title="Home")


@app.route('/settings', methods=['GET', 'POST'])
def redis_settings():
    global redis_client, redis_host, redis_port
    form = RedisConfigForm(request.form)
    if request.method == 'POST' and form.validate():
        redis_host = form.host.data
        redis_port = int(form.port.data)
        try:
            redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            redis_client.ping()
            flash('Redis settings updated successfully.', 'success')
        except redis.ConnectionError:
            flash('Failed to connect to Redis with the provided settings.', 'danger')
    return render_template('/settings/index.html', title="Settings", form=form, current_host=redis_host, current_port=redis_port)


if __name__ == '__main__':
    app.run(debug=True)
