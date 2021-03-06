#!/usr/bin/env python3
# coding:utf-8

import time
import os

from flask import Flask, request, render_template, session, flash, redirect, url_for, Response, jsonify, \
    send_from_directory
from jinja2 import Environment, FileSystemLoader
from werkzeug.utils import secure_filename

from utils import mylog, highlight, common
from models import Blog, Comment, User, next_id
import app_config


# 初始化flask的app
app = Flask(__name__)

UPLOAD_FOLDER = 'static/img/blogs'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])


@app.template_filter('datetime')
def datetime_filter(t):
    formatted_time = time.strftime('%b %d,%Y', time.localtime(t))
    return formatted_time


@app.template_filter('detail_time')
def detail_time_filter(t):
    formatted_time = time.strftime('%Y年%m月%d日 %H:%M:%S', time.localtime(t))
    return formatted_time


def get_avator_or_404(user_name):
    users = User.find_all('name= ?', [user_name])
    image = users[0].image
    return image


@app.route('/avatar/<user_name>.png')
def avatar(user_name):
    user_image = get_avator_or_404(user_name=user_name)
    return Response(user_image, mimetype='image/png')


def init_jinja2(config, **kw):
    mylog.info('init jinja2...')
    options = dict(
        autoescape=kw.get('autoescape', True),
        block_start_string=kw.get('block_start_string', '{%'),
        block_end_string=kw.get('block_end_string', '%}'),
        variable_start_string=kw.get('variable_start_string', '{{'),
        variable_end_string=kw.get('variable_end_string', '}}'),
        auto_reload=kw.get('auto_reload', True)
    )
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    mylog.info('set jinja2 template path: %s' % path)
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    config['__templating__'] = env


def create_app_and_init():
    # 初始化配置
    mode = app_config.init_config(app)

    init_jinja2(app.config, filters=dict(datetime=datetime_filter))
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    # 运行server
    app.run(debug=mode)


@app.route('/<username>')
def index(username=None):
    if username is not None and username == 'fantianwen':
        session['admin'] = True
    else:
        session['admin'] = False
    return redirect(url_for('welcome'))


@app.route('/')
def welcome():
    session['page_number'] = 1
    blogs = Blog.find_all(orderBy='created_at desc', limit=(0, 8))
    for blog in blogs:
        md = highlight.parse2markdown(blog.summary)
        blog.md_summary = md

    # 侧边栏的分类
    blog_categories = Blog.find_all(groupby='category')
    blogs_categories = []
    for category in blog_categories:
        blog_catrgory = Blog.find_all('category=?', [category.category])
        blogs_categories.append(blog_catrgory)
    return render_template('welcome.html', blogs=blogs, blogs_categories=blogs_categories)


@app.route('/page/<page_number>')
def show_page(page_number):
    int_page_number = int(page_number)
    session['page_number'] = int_page_number
    if page_number == 1:
        return redirect('/')
    blogs = Blog.find_all(orderBy='created_at desc', limit=((int_page_number - 1) * 8, 8))

    blog_categories = Blog.find_all(groupby='category')
    blogs_categories = []
    for category in blog_categories:
        blog_catrgory = Blog.find_all('category=?', [category.category])
        blogs_categories.append(blog_catrgory)

    return render_template('welcome.html', blogs=blogs, blogs_categories=blogs_categories)


@app.route('/write')
def write():
    return render_template('write.html')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def change_file_name(filename, id):
    afterfix = filename.rsplit('.', 1)[1]
    newname = [id, afterfix]
    return '.'.join(newname)


@app.route('/save_blog', methods=['POST'])
def save_blog():
    id = next_id()
    user_id = 'admin'
    user_name = 'fantianwen'
    file = request.files['blog_image']
    file.filename = change_file_name(file.filename, id)
    user_image = file.filename
    name = request.form['blog_title']
    summary = request.form['blog_summary']
    content = request.form['blog_content']
    category = request.form['blog_category']
    created_at = time.time()
    year = common.get_year(created_at)
    month = common.get_month(created_at)
    day = common.get_day(created_at)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    blog = Blog(id=id, user_id=user_id, user_name=user_name, user_image=user_image, name=name, summary=summary,
                content=content, category=category, created_at=created_at, year=year, month=month, day=day)
    blog.save()
    flash('保存成功')
    return render_template('/welcome.html')


# blog的图片资源
@app.route('/api/blog_image/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


@app.route('/blog/<id>', methods=['GET', 'POST'])
def blog_id(id):
    if request.method == 'POST':
        comment_content = request.form['comment_content']
        comment_name = request.form['comment_name']
        comment = Comment(id=next_id(), blog_id=id, user_id='guest', user_name=comment_name,
                          user_image='',
                          content=comment_content, created_at=time.time())
        comment.save()
        image = common.create_avatar_by_name(comment_name)
        user = User(id=next_id(), email='', passwd='', admin=0, name=comment_name,
                    image=image,
                    created_at=time.time())
        mylog.info(image)
        # TODO 先使用name来进行判定是否唯一，后期希望能够使用email来判断是否唯一
        _user = User.find_all('name= ?', [comment_name])
        if len(_user) == 0:
            user.save()
        flash('comment and new user had been saved successfully!')

    blog = Blog.find(id)
    md_text = highlight.parse2markdown(blog.content)
    blog.html_content = md_text
    comments = Comment.find_all('blog_id= ?', [id])
    return render_template('blogdetail.html', blog=blog, comments=comments)


@app.route('/archive', methods=['GET'])
def archive():
    # 获取年
    years = Blog.find_all(groupby='year')
    # 根据‘year’获取不同年的blog数据
    blogs = []
    for year_blog in years:
        year = year_blog.year
        # 根据year获取该年的blogs
        blogs_year = Blog.find_all('year= ?', [year], orderBy='created_at desc')
        mylog.info(blogs_year)
        blogs.append(blogs_year)
    return render_template('archive.html', blogs=blogs)


# api书写

# 根据blog的id获取blog
@app.route('/api/blog/<id>', methods=['GET'])
def get_blog(id):
    blog = Blog.find(id)
    return jsonify(id=blog.getValue('id'), name=blog.getValue('name'), summary=blog.getValue('summary'),
                   content=blog.getValue('content'))


@app.route('/api/blogs/<page_number>')
def get_blogs(page_number):
    int_page_number = int(page_number)
    blogs = Blog.find_all(orderBy='created_at desc', limit=((int_page_number - 1) * 8, 8))
    return jsonify(blogs=blogs)


if __name__ == '__main__':
    create_app_and_init()
