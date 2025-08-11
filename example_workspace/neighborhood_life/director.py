# Schedules alarms and executes actions at the right in-game times.
import math
import random
from typing import Dict, List
import services
from date_and_time import create_time_span
from sims4.tuning.tunable import TunableSingletonFactory
from sims4communitylib.utils.sims.common_sim_utils import CommonSimUtils
from sims4communitylib.utils.resources.common_alarm_utils import CommonAlarmUtils
from sims4communitylib.utils.location.common_location_utils import CommonLocationUtils
from sims4communitylib.utils.common_log_registry import CommonLogRegistry
from sims4communitylib.mod_support.common_mod_identity import CommonModIdentity
from .schedules import ScheduleBuilder, DailySchedule, TimeBlock
from .actions import ActionExecutor
from .news import NewsCenter
from .util import log, get_today_minutes, NLConfig, select_participant_sims

class NeighborhoodDirector:
    def __init__(self, cfg: NLConfig):
        self.cfg = cfg
        self._schedules: Dict[int, DailySchedule] = {}
        self._alarms: List[int] = []
        self._news = NewsCenter(cfg)
        self._executor = ActionExecutor(cfg)

    def start_for_today(self):
        sim_infos = select_participant_sims(self.cfg.participant_count)
        builder = ScheduleBuilder(self.cfg)
        self._schedules = builder.build_for_sims(sim_infos)
        self._schedule_alarms()

    def stop_all(self):
        for alarm_handle in list(self._alarms):
            CommonAlarmUtils.cancel_alarm(alarm_handle)
        self._alarms.clear()
        self._schedules.clear()

    def _schedule_alarms(self):
        now_min = get_today_minutes()
        for ds in self._schedules.values():
            for block in ds.blocks:
                delta = max(0, block.start_min - now_min)
                handle = CommonAlarmUtils.set_alarm(create_time_span(minutes=delta), self._on_block_start, repeating=False, data=(ds.sim_id, block))
                self._alarms.append(handle)
                end_handle = CommonAlarmUtils.set_alarm(create_time_span(minutes=delta + block.duration_min), self._on_block_end, repeating=False, data=(ds.sim_id, block))
                self._alarms.append(end_handle)
                log(f"Alarm set for Sim {ds.sim_id} block {block.action} in {delta} min, duration {block.duration_min}")

    def _on_block_start(self, alarm_handle, data):
        sim_id, block = data
        sim_info = CommonSimUtils.get_sim_info(sim_id)
        if sim_info is None:
            return
        self._news.post_start(sim_info, block)
        self._executor.execute(sim_info, block)

    def _on_block_end(self, alarm_handle, data):
        sim_id, block = data
        sim_info = CommonSimUtils.get_sim_info(sim_id)
        if sim_info is None:
            return
        self._news.post_end(sim_info, block)
        self._executor.cleanup(sim_info, block)
