#coding: utf-8
import pexpect,os,time
import threading
import re
class tomcat_sync():
    """此类用于tomcat的同步和重启
    1、同步采用linux-rsync命令，默认参数为同步整个文件夹
    2、重启是运行tomcat*目录下的bin/shutdown.sh和bin/startup.sh脚本，采用curl进行重启后的tomcat实例进行状态验证
    3、运行日志默认在脚本同路径下生成为tomcat_rsync.log
    """
    def __init__(self,source_catalog,ip,user,passwd,port,far_end_catalog):
        """定义封装linux命令所需要的参数需要的参数"""
        self.ip=ip
        self.user=user
        self.passwd=passwd
        self.port=port
        self.source_catalog=source_catalog
        self.far_end_catalog=far_end_catalog
        self.log_parameter="%s:%s::"%(self.ip,self.port)
    def ssh_order(self,order):
        """在使用rsync 和ssh IP 命令，都是采用ssh协议进行远程登陆，在登陆过程中需要输入密码
        在此脚本中使用pexpect模块进行密码的输入和公钥的"yes"。此函数需要输入实参"order"。
        """
        ssh_newkey = 'Are you sure you want to continue connecting' #ssh第一次连接所需要对公钥接收提升信息
        child = pexpect.spawn(order) #对pexpect.spawn进行实例化
        try:
            i = child.expect([pexpect.TIMEOUT, ssh_newkey, 'password: '])
            """expect支持list方式保存一组判断条件，
            1、pexpect.TIMEOUT 为shh超时
            2、ssh_newkey为对公钥接收的提示信息
            3、当命令交互提示符为password
            当我们输入ssh命令或者rsync命令会弹出交互界面让我们输入账号密码或着是yes/no,当命令交互的提示信息
            和我们定义expect list匹配时会返回list匹配元素的索引值
            """
            if i == 0:
                os.system('echo "%s-ERR---SSH登陆超时,请检查网络%s--%s" >> tomcat_rsync.log' %(self.log_parameter,child.before,child.after))
                return None
            if i == 1:
                child.sendline('yes')  #当ssh连接时让需要我们同意接收公钥时输入"yes"
                child.expect('password: ') #输入yes命令交互会提示我们输入密码，'password: '用来匹配
                i = child.expect([pexpect.TIMEOUT, 'password: ']) #确认公钥后需要输入密码
                if i == 0: #ssh超时
                    os.system('echo "%s-ERR---SSH登陆超时,请检查网络" >> tomcat_rsync.log'%(self.log_parameter))
                    return None
            child.sendline(self.passwd)  #输入密码
            child.expect(pexpect.EOF)
            return str(child.before.strip())

        except Exception as err:
            """输出错误日志"""
            os.system('echo "%s-ERR---%s" >> tomcat_rsync.log' % (self.log_parameter,str(err)))
            os.system('echo "%s-ERR---%s" >> tomcat_rsync.log' % (self.log_parameter,str(order)))
            os.system('echo "%s-ERR-程序停止运行" >> tomcat_rsync.log' % self.log_parameter)
            pass

    def file_sync(self):
        "将self的实参封合成用来同步的rsync实际命令，并调用ssh_order函数来执行合成后的命令"
        rsync_order='rsync -ar  %s  %s@%s:%s   --delete' \
                    % (self.source_catalog, self.user,
                       self.ip, self.far_end_catalog+'webapps/') ##rsync命令合成
        os.system('echo "%s-info---同步命令%s:准备执行tomcat重启" >> tomcat_rsync.log' % (self.log_parameter,rsync_order))
        tomcat_sync.ssh_order(self,rsync_order)  ##调用ssh_order引入合成的命令
        return

    def restart_web(self):
        """重启tomcat和验证重启后的http服务是否正常运行
        1、验证服务器是否正常或关闭和启动采用获取进程数方式进行判断"""
        url = self.ip + ':' + self.port  ##将IP和端口号合成URL用来验证http状态
        stop_path = self.far_end_catalog + "bin/shutdown.sh"  ##拼接tomcat 停止脚本路径
        start_path = self.far_end_catalog + "bin/startup.sh"  ##拼接tomcat 启动脚本路径
        tomcat_PID_info = "/usr/bin/ps aux |grep %s |wc -l " % (self.far_end_catalog)
        stop_tomcat = "ssh  %s@%s  %s" % (self.user, self.ip, stop_path) ##合成tomcat 停止脚本命令
        start_tomcat="ssh  %s@%s  %s"%(self.user,self.ip,start_path)   ##合成tomcat 启动脚本命令
        tomcat_PID="ssh  %s@%s   %s " % (self.user, self.ip,tomcat_PID_info) #tomcat 进程数获取命令
        os.system('echo "%s-info---同步完成:准备执行tomcat重启" >> tomcat_rsync.log' % self.log_parameter)
        try:
            os.system('echo "%s-info---准备停止:%s" >> tomcat_rsync.log' % (self.log_parameter,stop_tomcat))
            self.ssh_order(stop_tomcat)      #调用ssh验证，先停止tomcat实例
            PID=self.ssh_order(tomcat_PID)
            PID=int(re.sub("\D","",PID))   #获取进程数
            """pexpect模块执行grep进行进程查询默认会有一个换行符和grep进程所以当进程正常关闭wc -l获取当行数应该为2"""
            if PID > 2: #当PID大于2表示进程没有正常关闭
                for i in range(10):
                    time.sleep(3);
                    self.ssh_order(stop_tomcat) ##执行for循环在运行一次tomcat关闭进程
                    PID = self.ssh_order(tomcat_PID)
                    PID = int(re.sub("\D", "", PID))
                    if PID < 3:break #当PID小于3表示进程正常关闭推出循环
                    elif i > 2  : #进程还未关闭的话执行pkill关闭程序，然后进入下一个循环
                        tomcat_kill="ssh  %s@%s pkill -9 %s" % (self.user, self.ip,self.far_end_catalog)
                        self.ssh_order(tomcat_kill)
            os.system('echo "%s-info---tomcat关闭成功" >> tomcat_rsync.log' % self.log_parameter)
            self.ssh_order(start_tomcat)     #调用ssh验证，启动tomcat实例
            PID = self.ssh_order(tomcat_PID)
            PID = int(re.sub("\D", "", PID))
            if PID  < 3:
                os.system('echo "%s-ERR---%tomcat进程无法启动成功" >> tomcat_rsync.log' % self.log_parameter)
                return
            os.system('echo "%s-info---tomcat进程，等待http状态码" >> tomcat_rsync.log' %self.log_parameter)
            http_status="curl -I -m 5 -o /dev/null -s -w %{http_code} "+url
            os.system('echo "%s-info---http状态码查询中：%s" >> tomcat_rsync.log' % (self.log_parameter,http_status))
            for i in range(200):#利用for循环获取http状态码直到状态码不为空退出循环程序执行完毕
                time.sleep(1)
                http_info = int(os.popen(http_status).read())
                os.system('echo "%s-info---正在执行第%s次查询" >> tomcat_rsync.log' % (self.log_parameter,i))
                if http_info != 0:
                    os.system('echo "%s-info---%s--http状态码:%s---程序结束" >> tomcat_rsync.log' % (self.log_parameter,url,http_info))
                    break
            return
        except Exception as err:
            os.system('echo "%s-ERR---%s" >> tomcat_rsync.log' % self.log_parameter,err)
            pass

class my_thread(threading.Thread):
    """定义线程类"""
    def __init__(self,source_catalog,ip,user,passwd,port,far_end_catalog):
        super().__init__(name=ip) #导入主函数实参
        self.__ip=ip
        self.__user=user
        self.__passwd=passwd
        self.__port=port
        self.__source_catalog=source_catalog
        self.__far_end_catalog=far_end_catalog
        self.__log_parameter = "%s:%s::" % (ip,port)
    def run(self):
        """配置run函数来定义初始化创建线程的内容"""
        try:
            a = tomcat_sync(source_catalog=self.__source_catalog, ip=self.__ip,
                            user=self.__user, passwd=self.__passwd, port=self.__port,
                            far_end_catalog=self.__far_end_catalog)  # tomcat_sync类初始化
            print("%s线程名称：%s" % (self.__ip,threading.current_thread().getName()))  ##打印进程相关信息
            a.file_sync()  # 调用同步函数
            time.sleep(3)
            a.restart_web()  # 调用重启函数
        except Exception as err:
            os.system('echo "%s-ERR---并发发生错误程序自动停止:%s" >> tomcat_rsync.log'%(self.__log_parameter,err))
            pass

def run_sync_tomcat(rsyc_data=dict):
    """
    文本格式：
    /rsync_test/webapps/++192.168.3.111++root++funo1234++/app/apache/tomcat6002/++6002
    同步源目录++IP++用户名++密码++同步目录+端口号
    """
    sync_list =[]
    os.system('echo "" > tomcat_rsync.log')
    for data in rsyc_data:
        source_path = data['source_path']
        rsyn_IP = data['rsyn_IP']
        login_user = data['login_user']
        login_passwd = data['login_passwd']
        aim_path = data['aim_path']
        for port in data['tomcat_port']:
            sync_list.append('%s++%s++%s++%s++%s%s/++%s++' % (source_path, rsyn_IP, login_user, login_passwd, aim_path, port, port))
    for i in sync_list: #遍历每一行
        price_split=i.split('++')  #将字符串劈分，"++"为劈分符
        port=price_split[5]
        process = my_thread(source_catalog=price_split[0],ip=price_split[1],user=price_split[2],
                            passwd=price_split[3],port=port,
                          far_end_catalog=price_split[4]) #索引list的元素来实例化MyProcess创建进程
        process.start()  #启动线程

def web_backups(path):
    """web备份,默认备份路径和脚本同一路径，文件名为web_backups"""
    print('cp -pr %s web_backups'%(path))
    os.system('cp -pr %s web_backups'%(path))


if __name__ == "__main__":
    rsyc_data="/app/apache/tomcat6001/webapps" #指定需要备份的目录
    web_backups(rsyc_data)
    rsyc_data = [{
        "source_path": "/rsync_test/webapps/",
        "rsyn_IP": "192.168.3.111",
        "login_user": "root",
        "login_passwd": "funo1234",
        "aim_path": "/app/apache/tomcat",
        "tomcat_port": ['6001','6002']
    },{
        "source_path": "/rsync_test/webapps/",
        "rsyn_IP": "192.168.3.110",
        "login_user": "root",
        "login_passwd": "funo1234",
        "aim_path": "/app/apache/tomcat",
        "tomcat_port": ['6001','6002']
    },]
    run_sync_tomcat(rsyc_data)
