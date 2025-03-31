from flask import Flask, render_template, request, send_file, url_for, jsonify
import os
import json
from jinja2 import Environment, FileSystemLoader
from datetime import datetime  # 引入时间模块
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import qrcode
from qrcode.image.pil import PilImage

app = Flask(__name__)
app_version = '1.0.0'

# 读取品牌信息和产品信息
with open('config/brands_info.json', 'r', encoding='utf-8') as f:
    brands_info = json.load(f)

with open('config/product_info.json', 'r', encoding='utf-8') as f:
    product_info = json.load(f)

# 读取附件信息
with open('config/accessories_info.json', 'r', encoding='utf-8') as f:
    accessories_info = json.load(f)

# 读取制造商信息
with open('config/vendor_info.json', 'r', encoding='utf-8') as f:
    vendor_info = json.load(f)

# 读取设备信息
with open('config/device_info.json', 'r', encoding='utf-8') as f:
    device_info = json.load(f)

# 固定的产品名称
product_names = list(product_info.keys())

@app.route('/')
def index():
    return render_template('index.html', app_version=app_version)

@app.route('/installed')
def installed():
    return render_template('installed.html', brands=brands_info, products=product_names, product_info=product_info)

@app.route('/product-accessories')
def productaccessories():
    return render_template('product-accessories.html', brands=brands_info, accessories=accessories_info)

@app.route('/package')
def label_form():
    return render_template('package.html', vendors=vendor_info)

@app.route('/device')
def device_label_form():
    return render_template('device.html', brands=brands_info, device_info=device_info)

@app.route('/generate_barcode')
def generate_barcode():
    serial = request.args.get('serial')
    if not serial:
        return "请提供序列号", 400

    # 选择条码类型，这里使用Code128
    CODE = barcode.get_barcode_class('code128')
    code = CODE(serial, writer=ImageWriter())

    # 设置条码图片的尺寸和分辨率
    options = {
        "write_text": False,
        "module_width": 0.4,  # 条码宽度
        "module_height": 15.0,  # 条码高度
        "dpi": 300  # 分辨率
    }

    # 生成条码图片
    buffer = BytesIO()
    code.write(buffer, options=options)
    buffer.seek(0)

    # 返回条码图片
    return send_file(buffer, mimetype='image/png')

@app.route('/generate_barcode_text')
def generate_barcode_text():
    serial = request.args.get('serial')
    if not serial:
        return "请提供序列号", 400

    # 选择条码类型，这里使用Code128
    CODE = barcode.get_barcode_class('code128')
    code = CODE(serial, writer=ImageWriter())

    # 设置条码图片的尺寸和分辨率
    options = {
        "write_text": True,
        "module_width": 0.4,  # 条码宽度
        "module_height": 15.0,  # 条码高度
        "dpi": 300  # 分辨率
    }

    # 生成条码图片
    buffer = BytesIO()
    code.write(buffer, options=options)
    buffer.seek(0)

    # 返回条码图片
    return send_file(buffer, mimetype='image/png')

@app.route('/generate_qrcode')
def generate_qrcode():
    serial = request.args.get('serial')
    if not serial:
        return "请提供序列号", 400

    # 生成二维码
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=1,
    )
    qr.add_data(serial)
    qr.make(fit=True)

    # 创建二维码图片
    img = qr.make_image(fill_color="black", back_color="white")

    # 将图片保存到内存中
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    # 返回二维码图片
    return send_file(buffer, mimetype='image/png')

@app.route('/generate', methods=['POST'])
def generate():
    brand = request.form['brand']
    model = request.form['model']
    serial_number = request.form['serial_number']
    products = request.form.getlist('product[]')
    quantities = request.form.getlist('quantity[]')
    product_serials = request.form.getlist('product_serial[]')
    date = request.form['date']
    show_download_link = 'show_download_link' in request.form

    # 处理产品信息
    product_details = []
    for i, product in enumerate(products):
        quantity = int(quantities[i])
        product_code = product_info.get(product, '')  # 获取产品编码，如果不存在则为空字符串
        serials = product_serials[i].split('\n')[:quantity]

        # 如果序列号包含N/A并且数量大于1，则全部填充为N/A
        if 'N/A' in serials and quantity > 1:
            serials = ['N/A'] * quantity

        for j in range(quantity):
            product_details.append({
                'name': product,
                'code': product_code,
                'serial': serials[j] if j < len(serials) else 'N/A'
            })

    # 如果产品信息不足30行，补充空表格
    while len(product_details) < 30:
        product_details.append({
            'name': '',
            'code': '',
            'serial': ''
        })

    # 获取Base64编码的条码图片
    barcode_base64 = request.form.get('barcode_base64')

    # 加载模板
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('installation-sheet.html')

    # 渲染模板时，确保路径使用服务器相对路径
    output = template.render(
        brand=brand,
        model=model,
        address=brands_info[brand]['address'],
        phone=brands_info[brand]['phone'],
        logo=url_for('static', filename=os.path.join('images', brands_info[brand]['logo']).replace("\\", "/")),  # 使用 url_for 构造路径
        serial_number=serial_number,
        products=product_details,
        date=date,
        show_download_link=show_download_link,
        barcode_url=barcode_base64  # 传递条码图片的Base64编码
    )

    # 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # 格式：年月日时分秒
    output_filename = f"generated_sheet_{timestamp}.html"
    output_relative_path = os.path.join('output', output_filename).replace("\\", "/")  # 相对路径
    output_path = os.path.join(os.getcwd(), 'static', output_relative_path)  # 绝对路径

    # 确保 static/output 目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 保存生成的 HTML 文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)

    # 返回生成文件的完整静态资源 URL
    return {
        'url': url_for('static', filename=output_relative_path, _external=True)  # 返回完整 URL
    }

@app.route('/generate_accessories', methods=['POST'])
def generate_accessories():
    brand = request.form['brand']
    model = request.form['model']
    sales_number = request.form['sales_number']
    serial_number = request.form['serial_number']
    accessories = request.form.getlist('accessory[]')
    quantities = request.form.getlist('quantity[]')
    accessory_serials = request.form.getlist('accessory_serial[]')
    date = request.form['date']

    # 处理附件信息
    accessory_details = []
    for i, accessory in enumerate(accessories):
        quantity = int(quantities[i])
        accessory_info = accessories_info.get(accessory, {})  # 获取附件信息，如果不存在则为空字典
        accessory_code = accessory_info.get('code', '')  # 获取物料编码，如果不存在则为空字符串
        accessory_unit = accessory_info.get('unit', '')  # 获取单位，如果不存在则为空字符串

        accessory_details.append({
            'name': accessory,
            'code': accessory_code,
            'quantity': quantity,
            'unit': accessory_unit  # 添加单位信息
        })

    # 如果附件信息不足30行，补充空表格
    while len(accessory_details) < 30:
        accessory_details.append({
            'name': '',
            'code': '',
            'quantity': '',
            'unit': ''
        })

    # 获取Base64编码的条码图片
    barcode_base64 = request.form.get('barcode_base64')

    # 加载模板
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('product-accessories-sheet.html')

    # 渲染模板时，确保路径使用服务器相对路径
    output = template.render(
        brand=brand,
        model=model,
        address=brands_info[brand]['address'],
        phone=brands_info[brand]['phone'],
        logo=url_for('static', filename=os.path.join('images', brands_info[brand]['logo']).replace("\\", "/")),  # 使用 url_for 构造路径
        sales=sales_number,  # 销售凭证号
        serial_number=serial_number,
        accessories=accessory_details,
        date=date,
        barcode_url=barcode_base64  # 传递条码图片的Base64编码
    )

    # 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # 格式：年月日时分秒
    output_filename = f"generated_accessories_sheet_{timestamp}.html"
    output_relative_path = os.path.join('output', output_filename).replace("\\", "/")  # 相对路径
    output_path = os.path.join(os.getcwd(), 'static', output_relative_path)  # 绝对路径

    # 确保 static/output 目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 保存生成的 HTML 文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)

    # 返回生成文件的完整静态资源 URL
    return {
        'url': url_for('static', filename=output_relative_path, _external=True)  # 返回完整 URL
    }

@app.route('/generate_label', methods=['POST'])
def generate_label():
    # 获取表单数据
    vendor = request.form['vendor']
    model = request.form['model']
    sales_order = request.form['sales_order']
    configurations = request.form['configurations'].split('\n')  # 将配置按行分割
    barcode_base64 = request.form.get('barcode_base64')

    # 获取制造商信息
    vendor_details = vendor_info.get(vendor, {})

    # 加载模板
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('package-label.html')

    # 渲染模板时，确保路径使用服务器相对路径
    output = template.render(
        model=model,
        sales_order=sales_order,
        place_of_origin=vendor_details.get('place_of_origin', ''),
        phone=vendor_details.get('phone', ''),
        manufacturer=vendor_details.get('manufacturer', ''),
        manufacturer_address=vendor_details.get('manufacturer_address', ''),
        factory=vendor_details.get('factory', ''),
        factory_address=vendor_details.get('factory_address', ''),
        configurations=configurations,
        barcode_url=barcode_base64  # 传递条码图片的Base64编码
    )

    # 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # 格式：年月日时分秒
    output_filename = f"generated_label_{timestamp}.html"
    output_relative_path = os.path.join('output', output_filename).replace("\\", "/")  # 相对路径
    output_path = os.path.join(os.getcwd(), 'static', output_relative_path)  # 绝对路径

    # 确保 static/output 目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 保存生成的 HTML 文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)

    # 返回生成文件的完整静态资源 URL
    return {
        'url': url_for('static', filename=output_relative_path, _external=True)  # 返回完整 URL
    }

@app.route('/generate_device_label', methods=['POST'])
def generate_device_label():
    # 获取表单数据
    brand = request.form['brand']
    model = request.form['model']
    serial_number = request.form['serial_number']
    power_parameters = request.form['power_parameters']
    configurations = request.form['configurations'].split('\n')  # 将配置按行分割
    icons = request.form.getlist('icon[]')  # 获取多个图标
    barcode_base64 = request.form.get('barcode_base64')

    # 获取设备信息
    device_details = device_info.get(brand, {})

    # 获取品牌信息
    brand_details = brands_info.get(brand, {})

    # 获取产品名称
    product_name = device_details.get('product_name', '')

    # 获取 logo 路径
    logo = url_for('static', filename=os.path.join('images', device_details.get('logo', '')).replace("\\", "/"))

    # 获取 manufacturer
    manufacturer = device_details.get('manufacturer', '')

    # 加载模板
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('device-label.html')

    # 渲染模板时，确保路径使用服务器相对路径
    output = template.render(
        brand=brand,
        model=model,
        serial_number=serial_number,
        power_parameters=power_parameters,
        configurations=configurations,
        product_name=product_name,  # 传递产品名称
        logo=logo,  # 传递 logo 路径
        manufacturer=manufacturer,  # 传递 manufacturer
        icons=icons,  # 传递图标列表
        barcode_url=barcode_base64  # 传递条码图片的Base64编码
    )

    # 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # 格式：年月日时分秒
    output_filename = f"generated_device_label_{timestamp}.html"
    output_relative_path = os.path.join('output', output_filename).replace("\\", "/")  # 相对路径
    output_path = os.path.join(os.getcwd(), 'static', output_relative_path)  # 绝对路径

    # 确保 static/output 目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 保存生成的 HTML 文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)

    # 返回生成文件的完整静态资源 URL
    return {
        'url': url_for('static', filename=output_relative_path, _external=True)  # 返回完整 URL
    }

@app.route('/history')
def history():
    output_dir = os.path.join('static', 'output')
    files = [f for f in os.listdir(output_dir) if f.endswith('.html')]

    # 获取文件的最后修改时间并排序
    files_with_time = [(f, os.path.getmtime(os.path.join(output_dir, f))) for f in files]
    files_with_time.sort(key=lambda x: x[1], reverse=True)  # 按时间降序排序

    # 解析文件名并进行友好显示
    friendly_files = []
    for f, _ in files_with_time:
        if f.startswith('generated_sheet_'):
            friendly_name = '装机单'
        elif f.startswith('generated_accessories_sheet_'):
            friendly_name = '产品附件清单'
        elif f.startswith('generated_label_'):
            friendly_name = '包装标签'
        elif f.startswith('generated_device_label_'):
            friendly_name = '设备标签'
        else:
            friendly_name = f  # 如果文件名不符合预期，保持原名

        friendly_files.append((f, friendly_name))

    return render_template('history.html', files=friendly_files)

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    file_path = os.path.join('static', 'output', filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {'message': '文件已删除'}, 200
    else:
        return {'message': '文件不存在'}, 404

@app.route('/raid_calculator', methods=['GET', 'POST'])
def raid_calculator():
    if request.method == 'POST':
        data = request.get_json()  # 获取JSON格式的数据
        mode = data['mode']
        raid_level = data['raid_level']
        disk_capacity = float(data['disk_capacity'])
        unit = data['unit']
        if unit == 'GB':
            disk_capacity /= 1024  # Convert GB to TB

        if mode == 'forward':
            num_disks = int(data['num_disks'])
            raid_before, raid_after, result = calculate_raid_forward(raid_level, disk_capacity, num_disks)

            # 如果返回的是错误提示信息
            if isinstance(result, str):
                return jsonify({'error': result}), 400

        elif mode == 'reverse':
            raid_after = float(data['raid_after'])
            if unit == 'GB':
                raid_after /= 1024  # Convert GB to TB
            num_disks, raid_before, result = calculate_raid_reverse(raid_level, disk_capacity, raid_after)

            # 如果返回的是错误提示信息
            if isinstance(result, str):
                return jsonify({'error': result}), 400

        # Convert TB to GB for display if needed
        if unit == 'GB':
            disk_capacity *= 1024
            raid_before *= 1024
            raid_after *= 1024
            result *= 1024

        return jsonify({
            'mode': mode,
            'raid_level': raid_level,
            'disk_capacity': disk_capacity,
            'num_disks': num_disks,
            'raid_before': raid_before,
            'raid_after': raid_after,
            'computer_recognized': result,
            'unit': unit
        })
    else:
        return render_template('raid_calculator.html', mode='forward', raid_level='0', raid_before=0, computer_recognized=0, unit='TB')

def calculate_raid_forward(raid_level, disk_capacity, num_disks):
    # 定义每种RAID级别所需的最小磁盘数
    min_disks_required = {
        '0': 2,
        '1': 2,
        '5': 3,
        '6': 4,
        '10': 4,
        '50': 6,
        '60': 8
    }

    # 检查磁盘数量是否满足要求
    if raid_level not in min_disks_required or num_disks < min_disks_required.get(raid_level, float('inf')):
        return None, None, f"RAID {raid_level} 需要至少 {min_disks_required.get(raid_level, '未知')} 块磁盘"

    if raid_level == '0':
        raid_before = disk_capacity * num_disks
        raid_after = raid_before
    elif raid_level == '1':
        raid_before = disk_capacity * num_disks
        raid_after = disk_capacity
    elif raid_level == '5':
        raid_before = disk_capacity * num_disks
        raid_after = disk_capacity * (num_disks - 1)
    elif raid_level == '6':
        raid_before = disk_capacity * num_disks
        raid_after = disk_capacity * (num_disks - 2)
    elif raid_level == '10':
        raid_before = disk_capacity * num_disks
        raid_after = disk_capacity * (num_disks // 2)
    elif raid_level == '50':
        raid_before = disk_capacity * num_disks
        raid_after = disk_capacity * (num_disks // 2) * (num_disks // 2 - 1)
    elif raid_level == '60':
        raid_before = disk_capacity * num_disks
        raid_after = disk_capacity * (num_disks // 2) * (num_disks // 2 - 2)
    else:
        return 0, 0, "未知的RAID级别"

    computer_recognized = raid_after * 0.93132
    return raid_before, raid_after, computer_recognized


def calculate_raid_reverse(raid_level, disk_capacity, raid_after):
    if raid_level == '0':
        num_disks = raid_after / disk_capacity
        raid_before = raid_after
    elif raid_level == '1':
        num_disks = raid_after / disk_capacity
        raid_before = raid_after
    elif raid_level == '5':
        num_disks = raid_after / disk_capacity + 1
        raid_before = num_disks * disk_capacity
    elif raid_level == '6':
        num_disks = raid_after / disk_capacity + 2
        raid_before = num_disks * disk_capacity
    elif raid_level == '10':
        num_disks = (raid_after / disk_capacity) * 2
        raid_before = num_disks * disk_capacity
    elif raid_level == '50':
        num_disks = ((raid_after / disk_capacity) ** 0.5 + 1) * 2
        raid_before = num_disks * disk_capacity
    elif raid_level == '60':
        num_disks = ((raid_after / disk_capacity) ** 0.5 + 2) * 2
        raid_before = num_disks * disk_capacity
    else:
        return 0, 0, 0

    computer_recognized = raid_after * 0.93132
    return int(num_disks), raid_before, computer_recognized

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)