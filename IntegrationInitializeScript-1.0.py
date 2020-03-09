import paramiko
import time
class integration():
    def __init__(self,ip,user='root',passwd='GKndd14@bd',system_version=7):
        self.ip=ip
        self.user=user
        self.passwd=passwd
        self.system_version=system_version
        self.client=None

    def ssh_connect(self):
        try:
            """paramiko ssh初始化连接"""
            print(self.ip,self.user,self.passwd)
            self.client=paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(hostname=self.ip, port=22, username=self.user, password=self.passwd,timeout=11)
        except BaseException as err  :
            print(err)
            return
    def alter_host_name(self,host_name):
        """修改系统主机名"""
        try:
            self.client.exec_command('echo "NETWORKING=YES" >> /etc/sysconfig/network')
            self.client.exec_command('echo "HOSTNAME=%s" >> /etc/sysconfig/network' %(host_name))
            if self.system_version==7:self.client.exec_command("hostnamectl set-hostname %s" %(host_name))
            stdin, stdout, stderr =self.client.exec_command('hostname')
        except BaseException as err  :
            print(err)
        else:
            print(stdout.read().decode('utf-8'))

    def stop_system_service(self):
        """停止系统服务"""
        service_name_6=['NetworkManager','rpcbind.socket','iptables']
        service_name_7=['NetworkManager','firewalld.service','rpcbind.socket',]
        """停止selinux"""
        print(self.system_version)
        if self.system_version == 6 or self.system_version == 7:
            self.client.exec_command('setenforce 0')
            self.client.exec_command('sed -i "s/enforcing\+/disabled/"  /etc/selinux/config')
            stdin, stdout, stderr =self.client.exec_command('cat /etc/selinux/config |grep ^SELINUX=')
            print(stdout.read().decode('utf-8'))
        else:print("停止服务没有匹配对应系统版本号")
        if self.system_version==7:
            for i in range(len(service_name_7)):
                self.client.exec_command("systemctl stop %s " %(service_name_7[i]))
                stdin, stdout, stderr=self.client.exec_command("systemctl disable %s " % (service_name_7[i]))
                if stderr.read().decode('utf-8')=="":print("systemctl disable %s  "%service_name_7[i])
                else:print("service no %s disable "%service_name_7[i])
        elif self.system_version==6:
            for i in range(len(service_name_6)):
                self.client.exec_command("service stop %s " % (service_name_6[i]))
                stdin, stdout, stderr=self.client.exec_command("systemctl disable %s " % (service_name_6[i]))
                if  stderr.read().decode('utf-8')=="":print("service disable %s  "%service_name_7[i])
                else:print("service no %s disable "%service_name_7[i])
        else:print("停止服务没有匹配对应系统版本号")

    def net_bond(self,net_na_a,net_na_b,ip,gatewat,net_type):
        """配置bond网卡"""
        path="/etc/sysconfig/network-scripts/"
        #1、file bond
        netwo = "TYPE=Ethernet\nDEVICE=bond0\nBOOTPROTO=none\nONBOOT=yes\nUSERCTL=NO\nBONDING_OPTS='mode=%s  miimon=100'\n"%net_type # backup：1---load：802.3ad
        net_info = "IPADDR=" + ip + "\n"+"NETMASK=255.255.255.0" + "\n"+"GATEWAY=" + gatewat + "\n"
        bond_info =netwo + net_info
        self.client.exec_command('touch %sifcfg-bond0'%path)
        self.client.exec_command('echo -e "%s" >%sifcfg-bond0'%(bond_info,path))
        stdin, stdout, stderr=self.client.exec_command('cat %s%s'%(bond_info,path))
        print(stdout.read().decode('utf-8'))
        #2、file mode_a\mode_b
        a_name = "ifcfg-" + net_na_a
        b_name = "ifcfg-" + net_na_b
        mode_a = "TYPE=Ethernet\nDEVICE=" + net_na_a + "\nONBOOT=yes\nBOOTPROTO=none\nMASTER=bond0\nSLAVE=yes\nUSERCTL=NO\n"
        mode_b = "TYPE=Ethernet\nDEVICE=" + net_na_b + "\nONBOOT=yes\nBOOTPROTO=none\nMASTER=bond0\nSLAVE=yes\nUSERCTL=NO\n"
        self.client.exec_command('echo -e "%s" >%s%s' % (mode_a, path,a_name))
        self.client.exec_command('echo -e "%s" >%s%s' % (mode_b, path,b_name))
        #3、重启网卡查看日志
        time.sleep(5)
        self.client.exec_command('service network restart')
        time.sleep(10)
        self.ssh_connect()
        stdin, stdout, stderr=self.client.exec_command('cat /proc/net/bonding/bond0')
        print(stdout.read().decode('utf-8'))

    def disk_mount(self,mkfs_file,disk_list=[]):
        """硬盘批量挂载"""
        for i in range(len(disk_list)):
            a = list(range(1, 50))
            #1、创建文件夹
            file_name=str(a[i])
            self.client.exec_command("mkdir -p /data%s" %(file_name))
            #2、格式化文件系统
            if mkfs_file=='xfs':
                stdin, stdout, stderr=self.client.exec_command("mkfs.%s -f /dev/%s" %(mkfs_file,disk_list[i]))
            else:
                stdin, stdout, stderr=self.client.exec_command("mkfs.%s -F /dev/%s" %(mkfs_file,disk_list[i]))
            print(stderr.read().decode('utf-8'))
            if stderr.read().decode('utf-8')=="":
                print("格式化成功:mkfs.%s -f /dev/%s" %(mkfs_file,disk_list[i]))
            else:
                print("磁盘无法正常格式化,退出程序:"+stderr.read().decode('utf-8'));break
            #3、写入/fstab
            time.sleep(4)
            stdin, stdout, stderr=self.client.exec_command("blkid /dev/%s |awk -F: '{print $2}'|awk  '{print $1}'"%(disk_list[i]))
            path=stdout.read().decode("utf-8").replace("\n","")
            print("准备挂载:"+path)
            disk_info = "%s  /data%s    %s     defaults 0 0" % (path,file_name,mkfs_file)
            self.client.exec_command("echo '%s' >> /etc/fstab"%(disk_info))
        # 4、挂载配置生效,输出结果
        self.client.exec_command("mount -a ")
        time.sleep(2)
        stdin, stdout, stderr = self.client.exec_command('df -hT')
        print(stdout.read().decode('utf-8'))

    def ssh_key(self):
        """ssh免密配置"""
        pass

# ssh=integration(ip='172.16.110.128',user='root',passwd='zhanghaibin')
# ssh.ssh_connect() #连接初始化
# ssh.alter_host_name(host_name='txtx_email')  #主机名修改
# ssh.stop_system_service()    #服务停止
# ssh.net_bond(net_na_a='ens34',net_na_b='ens38',ip='192.168.1.222',gatewat='192.168.1.1',net_type='802.3ad')  #bond初始化
# ssh.disk_mount(mkfs_file='ext4',disk_list=['sdb','sdc','sdd'])   #硬盘挂载
