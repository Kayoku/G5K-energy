# G5K-energy

## Compatibilities

| City | Node | Kind of PDU (from G5K doc) | Omegawatt | Kwapi | SNMP |
| ---- | ---- | -------------------------- | --------- | ----- | ---- |
| Lille | chetemi | APC vendors, 1 node = 2 PDU | X | X | X |
| Grenoble | dahu | Dedicated Wattmetre | X | X | X |
| Nantes | ecotype | No PDU | X | X | X |
| Lyon | nova | Dedicated Wattmetre | X | X | X |
| Rennes | paravance| EATON & APC vendors | X | X | X |
| Nancy | grisou | EATON & APC vendors | X | X | X |

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
- Know the compatible Node (README)
- Know the context for run the script (python version, inside/outside G5K, with G5K login...)
