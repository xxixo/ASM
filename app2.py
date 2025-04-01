import json
import redis

from flask import Flask, render_template, request, redirect, url_for, flash



def load_redis_config(config_path='configs/redis.json'):
    '''Завантажує конфігурацію Redis з JSON-файлу.'''
    try:
        with open(config_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {'host': 'localhost', 'port': 6379, 'db': 0, 'password': None}

def save_redis_config(config, config_path='configs/redis.json'):
    '''Зберігає конфігурацію Redis у JSON-файлі.'''
    with open(config_path, 'w') as file:
        json.dump(config, file, indent=4)

def setup_redis(app: Flask, config_path='configs/redis.json'):
    '''Налаштовує підключення Redis для Flask-додатка.'''
    config = load_redis_config(config_path)
    app.config['REDIS_HOST'] = config.get('host', 'localhost')
    app.config['REDIS_PORT'] = config.get('port', 6379)
    
    redis_client = redis.Redis(
        host=app.config['REDIS_HOST'],
        port=app.config['REDIS_PORT'],
        decode_responses=True
    )
    try:
        redis_client.ping()
        app.config['REDIS_STATUS'] = 'Підключено'
    except redis.ConnectionError:
        app.config['REDIS_STATUS'] = 'Помилка підключення'
        redis_client = None
    
    return redis_client




app = Flask(__name__)
app.secret_key = 'your_secret_key'
global redis_client
redis_client = setup_redis(app)
setting_modules = ['shema', 'redis']

@app.route('/')
def home():
    tables = redis_client.smembers("tables")
    return render_template('/home/index.html', title='Home', parent_link='/table',  left_nav_bar_items=tables)


@app.route('/table/<table_name>')
def table(table_name=None):
    tables = redis_client.smembers("tables")  # Retrieve all table names
    table_data = None

    if table_name:
        # Retrieve all key-value pairs (columns and values) for the selected table
        table_data = redis_client.hgetall(table_name)
        print(table_data)

    return render_template('/home/index.html',
                           title=f'Table - {table_name}',
                           parent_link='/table',
                           left_nav_bar_items=tables,
                           selected_table=table_name,
                           table_data=table_data)



@app.route('/settings')
def settings():
    # Модулі які повині налаштовуватись - можлтво колись буде файл з ними 

    return render_template('/settings/index.html', 
                           title='Settings', 
                           parent_link='/settings', 
                           left_nav_bar_items=setting_modules)


@app.route('/settings/redis', methods=['GET', 'POST'])
def settings_redis():
    if request.method == 'POST':
        new_config = {
            'host': request.form.get('host', 'localhost'),
            'port': int(request.form.get('port', 6379))}
        
        save_redis_config(new_config)
        global redis_client
        redis_client = setup_redis(app)
        if redis_client:
                flash('Конфігурація оновлена та підключення успішне!', 'success')
        else:
                flash('Конфігурація збережена, але підключення не вдалося!', 'error')
            
        return redirect(url_for("settings"))   
                
    current_config = load_redis_config()
    return render_template(f'/settings/modules/redis/redis.html',
                           title='Settings',
                           parent_link='/settings', 
                           left_nav_bar_items=setting_modules, 
                           config=current_config)
    

@app.route('/settings/shema', methods=['GET'])
def setting_schema():
    tables = redis_client.smembers("tables")
    return render_template('/settings/modules/shema/shema.html',
                           title='Settings',
                           parent_link='/settings',
                           left_nav_bar_items=setting_modules,
                           tables=tables)

@app.route('/settings/schema/table/<table_name>', methods=['GET', 'POST'])
def manage_table(table_name):
    if request.method == 'POST':
        action = request.form.get('action')
        column_name = request.form.get('column_name')
        new_column_name = request.form.get('new_column_name')

        if action == 'add' and column_name:
            redis_client.hset(table_name, column_name, '')  # Add a new column with an empty value
            flash(f'Column "{column_name}" added to table "{table_name}".', 'success')

        elif action == 'rename' and column_name and new_column_name:
            if redis_client.hexists(table_name, column_name):
                value = redis_client.hget(table_name, column_name)
                redis_client.hdel(table_name, column_name)
                redis_client.hset(table_name, new_column_name, value)
                flash(f'Column "{column_name}" renamed to "{new_column_name}" in table "{table_name}".', 'success')
            else:
                flash(f'Column "{column_name}" does not exist in table "{table_name}".', 'error')

        elif action == 'delete' and column_name:
            if redis_client.hdel(table_name, column_name):
                flash(f'Column "{column_name}" deleted from table "{table_name}".', 'success')
            else:
                flash(f'Column "{column_name}" does not exist in table "{table_name}".', 'error')

        return redirect(url_for('manage_table', table_name=table_name))

    # Retrieve all columns for the selected table
    columns = redis_client.hkeys(table_name)
    return render_template('/settings/modules/shema/manage_table.html',
                           title=f'Manage Table: {table_name}',
                           parent_link='/settings/shema',
                           table_name=table_name,
                           columns=columns)



@app.route('/settings/schema/create_table', methods=['POST'])
def create_table():
    table_name = request.form.get('table_name')
    if table_name and table_name not in redis_client.smembers("tables"):
        redis_client.sadd("tables", table_name)
        flash(f'Table {table_name} created.', 'success')
    return redirect(url_for('setting_schema'))

@app.route('/settings/schema/drop_table', methods=['POST'])
def drop_table():
    table_name = request.form.get('delete_table_name')
    if table_name and table_name in redis_client.smembers("tables"):
        redis_client.srem("tables", table_name)  # Remove the table name from the set
        redis_client.delete(table_name)  # Optionally delete the table's data
        flash(f'Table {table_name} dropped.', 'success')
    else:
        flash(f'Table {table_name} does not exist.', 'error')
    return redirect(url_for('setting_schema'))




if __name__ == '__main__':
    app.run(debug=True)