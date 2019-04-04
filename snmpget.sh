#!/bin/bash

val=0
cmd1="snmpget -Oqv -v2c -c public pdu-b3p1.lille.grid5000.fr iso.3.6.1.4.1.318.1.1.26.9.4.3.1.7.10"
cmd2="snmpget -Oqv -v2c -c public pdu-b3p2-1.lille.grid5000.fr iso.3.6.1.4.1.318.1.1.26.9.4.3.1.7.10"

while [ 1 ]
do
	req1=`eval $cmd1`
	req2=`eval $cmd2`
	res=$(($req1 + $req2))
	echo $res
	val=$res
done
