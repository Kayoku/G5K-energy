# G5K-energy

## Compatibilities

| City | Node | Kind of PDU (from G5K doc) | Omegawatt | Kwapi | SNMP |
| ---- | ---- | ---- | ---- | ---- | ---- |
| Lille | chetemi | APC vendors, 1 node = 2 PDU | X | X | O |
| Grenoble | dahu | Dedicated Wattmetre | O | X | X |
| Nantes | ecotype | No PDU | X | X | X |
| Lyon | nova | Dedicated Wattmetre | O | O | X |
| Rennes | paravance| EATON & APC vendors | X | O | X |
| Nancy | grisou | EATON & APC vendors | X | O | O |

## Omegawatt-sensor

The omegawatt script work only if you are inside the G5K network.

	usage: omegawatt-sensor.py [-h]
                       mongodb_uri mongodb_db mongodb_collection city_name
                       cluster_name node_name timestamp_start
                       timestamp_stop

## Kwapi-sensor

The kwapi-sensor can be run outside the G5K network.

	usage: kwapi-sensor.py [-h]
                       g5k_login g5k_pass mongodb_uri mongodb_db
                       mongodb_collection city_name cluster_name node_name
                       timestamp_start timestamp_stop

## SNMP-sensor

The SNMP-sensor works only if you are inside the G5K network because it needs to request PDU.
Also, you need to have python <= 3.6 (because G5K is in 3.5)

	usage: snmp-sensor.py [-h]
                      mongodb_uri mongodb_db mongodb_collection city_name
                      cluster_name node_name

## Todo

- Add PDU version in the output
