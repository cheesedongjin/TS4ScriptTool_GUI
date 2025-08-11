# Bootstrap: register zone load/unload and kick the daily scheduler.
# Requires Sims 4 Community Library (S4CL).

import services
import sims4
from sims4communitylib.events.zone_events import S4CLZoneLateLoadEvent, S4CLZoneUnloadEvent
from sims4communitylib.events.event_handling.common_event_registry import CommonEventRegistry
from .director import NeighborhoodDirector
from .util import NLConfig, log, ensure_singleton

_DIRECTOR_SINGLETON = None

@CommonEventRegistry.handle_events(S4CLZoneLateLoadEvent)
def _on_zone_late_load(event: S4CLZoneLateLoadEvent):
    global _DIRECTOR_SINGLETON
    zone_id = services.current_zone_id()
    log(f"Zone late load detected. Zone ID: {zone_id}")
    cfg = NLConfig.load()
    director = NeighborhoodDirector(cfg)
    _DIRECTOR_SINGLETON = ensure_singleton(_DIRECTOR_SINGLETON, director)
    _DIRECTOR_SINGLETON.start_for_today()

@CommonEventRegistry.handle_events(S4CLZoneUnloadEvent)
def _on_zone_unload(event: S4CLZoneUnloadEvent):
    global _DIRECTOR_SINGLETON
    if _DIRECTOR_SINGLETON is not None:
        log("Zone unload: stopping director and clearing alarms.")
        _DIRECTOR_SINGLETON.stop_all()
        _DIRECTOR_SINGLETON = None

def on_zone_load():
    pass

def on_zone_unload():
    pass
