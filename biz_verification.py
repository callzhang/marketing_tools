# 一个简单的网页服务，用于发送资料。步骤为：
# 1. 网页服务开启的时候，从Google sheet（public）的地址读取available的文档数据，数据表头为：name、description、url
# 2. 用户收到商务发送的url，打开网页，其中url包含文件名。
# 3. 用户填入邮箱地址，验证客户邮箱是否为公司邮箱（通过读取一个本地文件列表，判断是否为公司邮箱）
# 4. 如果邮箱为公司邮箱，调用mailgun接口，发送验证码到用户填写的邮箱；如果是个人邮箱（列表中的域名命中），则提示用户填写公司邮箱。
# 5. 验证码逻辑为：code = hash(email+name+timestamp)
# 6. 用户填写验证码，验证是否正确，如果正确，跳转到文件下载页面，如果错误，提示用户重新填写验证码。

import streamlit as st
from utils import is_valid_email, send_email_via_mailgun, is_valid_code, get_doc_url

# get doc url from name
st.set_page_config(page_title="🔓邮箱验证", page_icon="🔓")
st.title('商务资料下载')
doc_name = st.experimental_get_query_params().get('doc_name', [''])[0]
if not doc_name:
    st.error('请使用使用正确的链接')
    st.stop()
url = get_doc_url(doc_name)
if not url:
    st.error('文件不存在或已过期')
    st.stop()

# vars
valid_email = False


# body
info = st.empty()
info.info('请使用浏览器打开，不要使用微信打开')
col1, col2 = st.columns([0.8, 0.2])
email = col1.text_input('请输入您的公司邮箱地址：', key='email',
                        placeholder='公司邮箱地址', label_visibility='collapsed')
if email:
    if is_valid_email(email):
        valid_email = True
    else:
        st.toast('请输入公司邮箱地址')
send_code = col2.button('发送验证码', disabled=not valid_email)
col3, col4 = st.columns([0.8, 0.2])
code = col3.text_input('请输入验证码：', placeholder='六位验证码',
                       label_visibility='collapsed')
verify = col4.button('核实验证码', disabled=not code)
if send_code:
    with st.spinner('正在发送验证码...'):
        success = send_email_via_mailgun(email, doc_name)
        if success:
            st.toast('验证码已发送，请查收')
        else:
            st.toast(f'验证码发送失败，请稍后重试')
if verify:
    if is_valid_code(code, email, doc_name):
        with st.spinner('正在验证...'):
            url = get_doc_url(doc_name)
        info.success('验证成功，请点击链接进入查看')
        
        st.markdown(f'**[{doc_name}]({url})**')
    else:
        st.toast('验证码错误，请重新输入')
