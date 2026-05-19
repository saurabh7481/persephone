from __future__ import annotations

from typing import Any, TypeAlias

import numpy as np

StateDict: TypeAlias = dict[str, np.ndarray]
MetricRecord: TypeAlias = dict[str, Any]
EventRecord: TypeAlias = dict[str, Any]
BusRecord: TypeAlias = dict[str, Any]
