# coding=utf-8
import os,time
import paramiko

def host_name(name): #修改主机名
	a=os.system("echo 'NETWORKING=YES' >> /etc/sysconfig/network")
	a=os.system("echo 'HOSTNAME=%s' >> /etc/sysconfig/network" %(name))
	a=os.system("hostnamectl set-hostname %s" %(name))
	time.sleep(1)
	d = os.popen("hostname")
	print(d.read())


def sshclient(ip,user,psswd,port="22"):  #验证网络是否正常，获取光口MAC地址 需要登陆管理机10.47.224.1
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip, port=port, username=user, password=psswd)
    stdin, stdout, stderr = client.exec_command('ifconfig bond0 |grep "inet"|awk {print $1} ; cat /proc/net/bonding/bond0  |grep -E  "Slave Interface:|Permanent HW addr"')
    print(stdout.read().decode('utf-8'))
    client.close()

def iso_yum(ip,yum_ip,user='root',psswd='GKndd14@bd',):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip, port=22, username=user, password=psswd)
    stdin, stdout, stderr = client.exec_command('echo -e "[base]\nname=base\nbaseurl=ftp://%s/pub\ngpgcheck=0\nenabled=1" >/etc/yum.repos.d/base.repo'%yum_ip)
    print(stderr.read().decode('utf-8'))
    stdin, stdout, stderr = client.exec_command('yum clean all ; yum update -y ;yum repolist')
    print(stdout.read().decode('utf-8'))
    client.close()


def sys_stop():#系统服务禁止使用6.0系统
    sys_log=[]
    name_stop=['NetworkManager','firewalld.service','rpcbind.socket','iptables']
    a=os.system('type systemctl')
    selinux_sed = os.popen("sed -i 's/enforcing\+/disabled/'  /etc/selinux/config")
    time.sleep(2)
    selinux_cat = os.popen("cat /etc/selinux/config |grep ^SELINUX=")
    sys_log.append('selinux : %s' %selinux_cat.read())
    if a==0:
        for i in range(len(name_stop)):
            get_back=os.system('systemctl stop %s' % (name_stop[i]))
            if get_back ==0:
                a=os.system('systemctl disable %s' % (name_stop[i]))
                sys_log.append(name_stop[i]+' server stop')
                pass
            else:
                sys_log.append(name_stop[i] + ' server error')

    else:
        for i in range(len(name_stop)):
            get_back = os.system('service %d stop' % (name_stop[i]))
            if get_back == 0:
                a = os.system('chkconfig %d off' % (name_stop[i]))
                sys_log.append(name_stop[i] + '\t server stop')
            else:
                sys_log.append(name_stop[i] + '\t server error')
    for i in range(len(sys_log)):
        print (sys_log[i]+'\n')



def network_info(net_na_1,net_na_2,ip,gatewat="10.45.179.254"): #配置bond
	a_name="ifcfg-"+net_na_1
	b_name="ifcfg-"+net_na_2
	bond_file= open("ifcfg-bond0", "w")
	netwo="TYPE=Ethernet\nDEVICE=bond0\nBOOTPROTO=none\nONBOOT=yes\nUSERCTL=NO\nBONDING_OPTS='mode=1  miimon=100'\n" #802.3ad
	ipadd="IPADDR="+ip+"\n"
	netma="NETMASK=255.255.255.0"+"\n"
	gatem="GATEWAY="+gatewat+"\n"
	mode_a="TYPE=Ethernet\nDEVICE="+net_na_1+"\nONBOOT=yes\nBOOTPROTO=none\nMASTER=bond0\nSLAVE=yes\nUSERCTL=NO\n"
	mode_b="TYPE=Ethernet\nDEVICE="+net_na_2+"\nONBOOT=yes\nBOOTPROTO=none\nMASTER=bond0\nSLAVE=yes\nUSERCTL=NO\n"
	bond_info=netwo+ipadd+netma+gatem
	bond_file.write(bond_info)
	bond_file.close()
	bond_a= open(a_name, "w")
	bond_a.write(mode_a)
	bond_a.close()
	bond_b= open(b_name, "w")
	bond_b.write(mode_b)
	bond_b.close()
	mv_l_1="mv -f  /etc/sysconfig/network-scripts/"+a_name+"   /dev/null"
	mv_l_2="mv -f  /etc/sysconfig/network-scripts/"+b_name+"   /dev/null"
	a=os.system(mv_l_1)
	a=os.system(mv_l_2)
	mv_l_3="mv ./"+a_name+" /etc/sysconfig/network-scripts"
	mv_l_4="mv ./"+b_name+" /etc/sysconfig/network-scripts"
	os.system(mv_l_3)
	os.system(mv_l_4)
	os.system("mv ./ifcfg-bond0 /etc/sysconfig/network-scripts")
	os.system('service network restart')
	time.sleep(10)
	os.system('cat /proc/net/bonding/bond0')



def disk_name(disk_list=[]): #磁盘挂载
        for i in range(len(disk_list)):
                a=["01","02","03","04","05","06","07","08","09","10","11","12","13","14","15","16","17","18","19","20","21","22","23","24","25","26"]
                c=str(a[i])
                os.system("mkdir -p /data%s" %(c))
                os.system("mkfs.xfs -f /dev/%s" %(disk_list[i]))
                a=os.popen("blkid /dev/%s |awk -F: '{print $2}'|awk  '{print $1}'"%(disk_list[i]))
                b=a.read()
                b=b.replace("\n","")
                disk_info="%s  /data%s    xfs     defaults 0 0"%(b,c)
                print(disk_info)
                os.system("echo '%s' >> /etc/fstab"%(disk_info) )
                time.sleep(0.5)
        os.system("mount -a ")

def ssh_avoid_pass(ip,passs='GKndd14@bd',create_key=0):
    try:
        if len(ip)==None:
            print("请输入IP")
            return
        if create_key == 1:
            os.system('rm -rf  ~/.ssh/*')
            os.system('ssh-keygen -t rsa -P ""  -f ~/.ssh/id_rsa')
            time.sleep(1)
            os.system('cp -p ~/.ssh/id_rsa.pub ~/.ssh/authorized_keys')
        time.sleep(1)
        print("sshpass -p %s scp -p -o StrictHostKeyChecking=no /root/.ssh/* root@%s:/root/.ssh"%(passs,ip))
        print("sshpass -p %s ssh -o StrictHostKeyChecking=no root@%s  'mkdir /root/.ssh/' " % (passs, ip))
        os.system("sshpass -p %s ssh -o StrictHostKeyChecking=no root@%s  'mkdir /root/.ssh/' " % (passs, ip))
        os.system("sshpass -p %s scp -p -o StrictHostKeyChecking=no /root/.ssh/* root@%s:/root/.ssh"%(passs,ip))
    except Exception as err:
        print("发生错误：%s"%err)

#sys_stop()
disk_name(["sdb","sdc","sdd","sde","sdf","sdg","sdh","sdi","sdj","sdk","sdl","sdm","sdn","sdo","sdp","sdq","sdr","sds","sdt","sdu","sdv","sdw","sdx","sdy"])
host_name("edc-rta-cn24")
network_info("ens4f0","ens5f1",'10.45.179.121')
#ssh_avoid_pass(ip,'zhanghaibin0.',1)
#for i in range(26,27):
#    ip="10.45.179."+str(i)
#    print(ip)
#    ssh_avoid_pass(ip)
#iso_yum("10.45.179.115","10.45.179.1")
