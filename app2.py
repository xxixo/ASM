from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'your_secret_key'


@app.route('/')
def home():
    tables = ['Tenants', 'Sensors', 'Tasks', 'Assets']
    return render_template('/home/index.html', title="Home",  left_nav_bar_items=tables)


@app.route('/settings')
def settings():
    modules = ['Schema', 'Redis']
    return render_template('/settings/index.html', title="Settings", left_nav_bar_items=modules)



if __name__ == '__main__':
    app.run(debug=True)