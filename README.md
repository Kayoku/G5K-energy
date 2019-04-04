# G5K-energy

## Omegawatt-sensor

The omegawatt script work only if you are inside the G5K network.

	usage: omegawatt-sensor.py [-h]
                           city_name cluster_name node_name timestamp_start
                           timestamp_stop	

## Kwapi-sensor

The kwapi-sensor can be run outside the G5K network.

	usage: kwapi-sensor.py [-h]
                       g5k_login g5k_pass city_name cluster_name node_name
                       timestamp_start timestamp_stop

## SNMP-sensor

The SNMP-sensor works only if you are inside the G5K network because it needs to request PDU.

	usage: snmp-sensor.py [-h] g5k_login g5k_pass city_name cluster_name node_name

## Todo

- Make them write output in a MongoDB
- Add PDU version in the output

