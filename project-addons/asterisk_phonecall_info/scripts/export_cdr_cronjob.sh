#! /bin/sh
# -*- encoding: utf-8 -*-
#
# Script to send the cdr log to an external server

# yum --enablerepo=epel -y install sshpass 
# chmod +x the_file_name

password="password"
username="user"
Ip="IP"
sshpass -p $password scp -P 2220/var/log/asterisk/cdr-csv/Master.csv $username@$Ip:/opt/odoo/Leistung/project-addons/asterisk_phonecall_info/cdr_logs/Master.csv
echo "file exported"