#### consumerDicts:
```python
[ # indexed from 0 - 35135
  consumerDict
]
```

#### consumerDict:
```python

{
  'graph' : network graph (networkx directed graph),
  'flowDict' : minimum cost flow dictionary,

  sink id (string) :  [ # counting index
                        {
                          'from' : source index (integer),
                          'to' : sink index (integer),
                          'distance' : distance in meters (integer),
                          'energy' : energy in watt hours (integer)
                        }
                      ],
}
```
#### producerDicts:
```python
[ # indexed from 0 - 35135
  producerDict
]
```

#### producerDict:

```python
{
  'graph' : network graph (networkx directed graph),
  'flowDict' : minimum cost flow dictionary,

  source id (str) :   [ # counting index
                        {
                        'from' : source index (int),
                        'to' : sink index (int),
                        'distance' : distance in meters (int),
                        'energy' : energy in watt hours (int)
                        }
                      ]
}
```

#### flowDict:

```python
{
  source index (int) :  {
                          sink index (int) : energy in watt hours (int)
                        }
}
```

#### graph:

```python
[ # counting index
  {
    'id' : node id (str),
    'location' : node location (tuple (lat, long)),
    'demand' : node demand (int)
  }
]
```

#### userDicts:
User specific dictionary cointaining the incoming connections for each time slice (indexed as dictionary --> missing time slices possible).

```python
{
  time slice (int) :  [ # counting index
                        connectionDict
                      ]
}
```


#### connectionDict
Describes a specific connection
```python
{
  'fromId' : source id (str),
  'toId' : sink id (str),
  'from' : source location (tuple (lat, long)),
  'to' : sink location (tuple (lat, long)),
  'energy' : energy in watt hours (int)
}
```

#### aggregatedConnection:
Cumulated energy from a specific location
```python
{
  'energy' : energy in watt hours (int),
  'location' : source location (tuple (lat, long))
}
```

#### aggregatedConnections:

```python
{
  source id (str) : aggregated connection (dictionary)
}
```

#### paths:

```python
[ # counting index
  [
    source location (tuple (lat, long)),
    sink location (tuple (lat, long))
  ]
]
```
