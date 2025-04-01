from flask import Flask, render_template, request, redirect, url_for, flash
import redis
import re
import json
from wtforms import Form, StringField, SelectField, validators

app = Flask(__name__)
app.secret_key = 'your_secret_key'

CONFIG_FILE = 'redis_config.json'

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'host': 'localhost', 'port': 6379}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

# Завантажуємо початкові налаштування Redis
config = load_config()
redis_host = config['redis_host']
redis_port = config['redis_port']
redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

def validate_ip(ip):
    pattern = r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$'
    return re.match(pattern, ip)

def validate_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
    return re.match(pattern, email)

class FieldForm(Form):
    field_name = StringField('Field Name', [validators.DataRequired()])
    field_type = SelectField('Field Type', choices=[('text', 'Text'), ('number', 'Number'), ('ip', 'IP Address'),
                                                    ('email', 'Email'), ('select', 'Dropdown'), ('multiselect', 'Multi-Select')])
    field_value = StringField('Value (comma-separated for dropdowns)')

class RedisConfigForm(Form):
    host = StringField('Redis Host', [validators.DataRequired()])
    port = StringField('Redis Port', [validators.DataRequired()])

@app.route('/')
def index():
    tables = redis_client.smembers("tables")
    return render_template('index.html', tables=tables)

@app.route('/create_table', methods=['POST'])
def create_table():
    table_name = request.form.get('table_name')
    if table_name and table_name not in redis_client.smembers("tables"):
        redis_client.sadd("tables", table_name)
        flash(f'Table {table_name} created.', 'success')
    return redirect(url_for('index'))

@app.route('/table/<table_name>', methods=['GET', 'POST'])
def table_detail(table_name):
    form = FieldForm(request.form)
    fields = redis_client.hgetall(table_name)
    
    if request.method == 'POST' and form.validate():
        field_name = form.field_name.data
        field_type = form.field_type.data
        field_value = form.field_value.data

        if field_type == 'number' and not field_value.isdigit():
            flash('Invalid number!', 'danger')
        elif field_type == 'ip' and not validate_ip(field_value):
            flash('Invalid IP address!', 'danger')
        elif field_type == 'email' and not validate_email(field_value):
            flash('Invalid email!', 'danger')
        else:
            redis_client.hset(table_name, field_name, f'{field_type}:{field_value}')
            flash(f'Field {field_name} added.', 'success')
            return redirect(url_for('table_detail', table_name=table_name))
    
    return render_template('table.html', table_name=table_name, fields=fields, form=form)

@app.route('/table/<table_name>/add_row', methods=['POST'])
def add_row(table_name):
    data = request.form.to_dict()
    row_id = redis_client.incr(f"{table_name}:row_id")
    for field, value in data.items():
        redis_client.hset(f"{table_name}:row:{row_id}", field, value)
    flash(f'Row {row_id} added to {table_name}.', 'success')
    return redirect(url_for('table_detail', table_name=table_name))

@app.route('/table/<table_name>/view_rows')
def view_rows(table_name):
    row_ids = [key.split(":")[-1] for key in redis_client.keys(f"{table_name}:row:*")]
    rows = []
    for row_id in row_ids:
        row_data = redis_client.hgetall(f"{table_name}:row:{row_id}")
        rows.append({'id': row_id, 'data': row_data})
    return render_template('view_rows.html', table_name=table_name, rows=rows)

@app.route('/redis_settings', methods=['GET', 'POST'])
def redis_settings():
    global redis_client, redis_host, redis_port
    form = RedisConfigForm(request.form)
    if request.method == 'POST' and form.validate():
        redis_host = form.host.data
        redis_port = int(form.port.data)
        new_config = {'host': redis_host, 'port': redis_port}
        save_config(new_config)
        try:
            redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            redis_client.ping()
            flash('Redis settings updated successfully.', 'success')
        except redis.ConnectionError:
            flash('Failed to connect to Redis with the provided settings.', 'danger')
    return render_template('redis_settings.html', form=form, current_host=redis_host, current_port=redis_port)

if __name__ == '__main__':
    app.run(debug=True)
