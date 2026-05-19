# API reference

Generated from docstrings on the live source.

## Motor (Level 0 + Level 1)

```{eval-rst}
.. autoclass:: mks_servo.Motor
   :members:
```

## MotorBus

```{eval-rst}
.. autoclass:: mks_servo.MotorBus
   :members:

.. autoclass:: mks_servo.BusEntry
   :members:
```

## Profile

```{eval-rst}
.. autoclass:: mks_servo.Profile
   :members:
```

## Namespaces (Level 2)

```{eval-rst}
.. autoclass:: mks_servo.AdvancedNamespace
   :members:

.. autoclass:: mks_servo.DiagnosticsNamespace
   :members:
```

## Characterization

```{eval-rst}
.. autoclass:: mks_servo.CharacterizationSuite
   :members:

.. autoclass:: mks_servo.SuiteResult
   :members:

.. autoclass:: mks_servo.P1Result
   :members:

.. autoclass:: mks_servo.P3Result
   :members:

.. autoclass:: mks_servo.P5Result
   :members:

.. autoclass:: mks_servo.S2Result
   :members:
```

## Raw driver (Level 3)

```{eval-rst}
.. autoclass:: mks_servo.RawDriver
   :members:

.. autoclass:: mks_servo.MotorStatus
   :members:

.. autofunction:: mks_servo.make_raw_driver
```

**`mks_servo.DRIVER_REGISTRY`** — module-level `dict[str, type]` mapping a
model name (e.g. `"servo42d"`) to its `RawDriver` class. `make_raw_driver`
looks the model up here, so registering a new driver is one line:
`DRIVER_REGISTRY["servo57d"] = MyServo57Driver`.

## Transport

```{eval-rst}
.. autoclass:: mks_servo.SharedTransport
   :members:
```

## Constants

```{eval-rst}
.. autoclass:: mks_servo.WorkMode
   :members:

.. autoclass:: mks_servo.Direction
   :members:

.. autoclass:: mks_servo.BaudRate
   :members:

.. autoclass:: mks_servo.OpCode
   :members:
```

## Exceptions

```{eval-rst}
.. autoexception:: mks_servo.MKSError

.. autoexception:: mks_servo.CommTimeout

.. autoexception:: mks_servo.ChecksumError

.. autoexception:: mks_servo.ProtocolError

.. autoexception:: mks_servo.MotorFault

.. autoexception:: mks_servo.CalibrationFailed

.. autoexception:: mks_servo.ProfileError

.. autoexception:: mks_servo.LimitExceeded

.. autoexception:: mks_servo.MotorNotAttached
```
