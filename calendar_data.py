import datetime
from copy import deepcopy
from typing import cast, Dict, List, Optional
import json
import os
import time

from gregorian_calendar import GregorianCalendar

KEY_TASKS = "tasks"
KEY_USERS = "users"
KEY_NORMAL_TASK = "normal"
KEY_REPETITIVE_TASK = "repetition"
KEY_REPETITIVE_HIDDEN_TASK = "hidden_repetition"
KEY_REPEAT_BEGIN = "customized_repeat_begin"
KEY_REPEAT_VALUE = "repetition_value"
KEY_REPEAT_TOTAL = "customized_total_repeat"


class CalendarData:
    REPETITION_TYPE_WEEKLY = "w"
    REPETITION_TYPE_MONTHLY = "m"
    REPETITION_SUBTYPE_WEEK_DAY = "w"
    REPETITION_SUBTYPE_MONTH_DAY = "m"
    # customized type
    REPETITION_TYPE_CUSTOMIZED = "c"

    def __init__(self, data_folder: str) -> None:
        self.data_folder = data_folder

    def load_calendar(self, filename: str) -> Dict:
        with open(os.path.join(".", self.data_folder, "{}.json".format(filename))) as file:
            contents = json.load(file)
        if type(contents) is not dict:
            raise ValueError("Error loading calendar from file '{}'".format(filename))
        return cast(Dict, contents)

    def users_list(self, data: Optional[Dict] = None, calendar_id: Optional[str] = None) -> List:
        if data is None:
            if calendar_id is None:
                raise ValueError("Need to provide either calendar_id or loaded data")
            else:
                data = self.load_calendar(calendar_id)
        if KEY_USERS not in data.keys():
            raise ValueError("Incomplete data for calendar id '{}'".format(calendar_id))

        return cast(List, data[KEY_USERS])

    def user_details(self, username: str, data: Optional[Dict] = None, calendar_id: Optional[str] = None) -> Dict:
        if data is None:
            if calendar_id is None:
                raise ValueError("Need to provide either calendar_id or loaded data")
            else:
                data = self.load_calendar(calendar_id)
        if KEY_USERS not in data.keys():
            raise ValueError("Incomplete data for calendar id '{}'".format(calendar_id))

        return cast(Dict, data[KEY_USERS][username])

    def tasks_from_calendar(self, year: int, month: int, view_past_tasks: Optional[bool] = True,
                            data: Optional[Dict] = None, calendar_id: Optional[str] = None) -> Dict:
        if data is None:
            if calendar_id is None:
                raise ValueError("Need to provide either calendar_id or loaded data")
            else:
                data = self.load_calendar(calendar_id)

        if KEY_TASKS not in data.keys():
            raise ValueError("Incomplete data for calendar id '{}'".format(calendar_id))

        if not all([KEY_NORMAL_TASK in data[KEY_TASKS].keys(),
                    KEY_REPETITIVE_TASK in data[KEY_TASKS].keys(),
                    KEY_REPETITIVE_HIDDEN_TASK in data[KEY_TASKS].keys()]):
            raise ValueError("Incomplete data for calendar id '{}'".format(calendar_id))

        tasks = {}  # type: Dict
        if str(year) in data[KEY_TASKS][KEY_NORMAL_TASK]:
            if str(month) in data[KEY_TASKS][KEY_NORMAL_TASK][str(year)]:
                tasks = data[KEY_TASKS][KEY_NORMAL_TASK][str(year)][str(month)]

        if not view_past_tasks:
            current_day, current_month, current_year = GregorianCalendar.current_date()
            if year < current_year:
                tasks = {}
            elif year == current_year:
                if month < current_month:
                    tasks = {}
                else:
                    for day in tasks.keys():
                        if month == current_month and int(day) < current_day:
                            tasks[day] = []

        return tasks

    def task_from_calendar(self, calendar_id: str, year: int, month: int, day: int, task_id: int) -> Dict:
        data = self.load_calendar(calendar_id)

        year_str = str(year)
        month_str = str(month)
        day_str = str(day)

        for index, task in enumerate(data[KEY_TASKS][KEY_NORMAL_TASK][year_str][month_str][day_str]):
            if task["id"] == task_id:
                task["repeats"] = False
                task["date"] = self.date_for_frontend(year=year, month=month, day=day)
                return cast(Dict, task)
        raise ValueError("Task id '{}' not found".format(task_id))

    def repetitive_task_from_calendar(self, calendar_id: str, year: int, month: int, task_id: int) -> Dict:
        data = self.load_calendar(calendar_id)

        task = [task for task in data[KEY_TASKS][KEY_REPETITIVE_TASK] if task["id"] == task_id][0]  # type: Dict
        task["repeats"] = True
        task["date"] = self.date_for_frontend(year=year, month=month,
                                              day=int(str(task[KEY_REPEAT_BEGIN]).split("-")[2]))
        return task

    @staticmethod
    def date_for_frontend(year: int, month: int, day: int) -> str:
        return "{0}-{1:02d}-{2:02d}".format(int(year), int(month), int(day))

    def add_repetitive_tasks_from_calendar(
            self, year: int, month: int, data: Dict, tasks: Dict, view_past_tasks: Optional[bool] = True
    ) -> Dict:
        current_day, current_month, current_year = GregorianCalendar.current_date()

        repetitive_tasks = self._repetitive_tasks_from_calendar(
            year=year,
            month=month,
            month_days=GregorianCalendar.month_days_with_weekday(year=year, month=month),
            data=data)

        for day, day_tasks in repetitive_tasks.items():
            if not view_past_tasks:
                if year < current_year:
                    continue
                if year == current_year:
                    if month < current_month or (month == current_month and int(day) < current_day):
                        continue
            if day not in tasks:
                tasks[day] = []
            for task in day_tasks:
                tasks[day].append(task)

        return tasks

    @staticmethod
    def add_task_to_list(tasks: Dict, day: int, new_task: Dict) -> None:
        day_str = str(day)
        if day_str not in tasks:
            tasks[day_str] = []
        tasks[day_str].append(new_task)

    def delete_task(self, calendar_id: str, year_str: str, month_str: str, day_str: str, task_id: int) -> None:
        deleted = False
        data = self.load_calendar(calendar_id)

        if (year_str in data[KEY_TASKS][KEY_NORMAL_TASK] and
                month_str in data[KEY_TASKS][KEY_NORMAL_TASK][year_str] and
                day_str in data[KEY_TASKS][KEY_NORMAL_TASK][year_str][month_str]):
            for index, task in enumerate(data[KEY_TASKS][KEY_NORMAL_TASK][year_str][month_str][day_str]):
                if task["id"] == task_id:
                    data[KEY_TASKS][KEY_NORMAL_TASK][year_str][month_str][day_str].pop(index)
                    deleted = True

        if not deleted:
            for index, task in enumerate(data[KEY_TASKS][KEY_REPETITIVE_TASK]):
                if task["id"] == task_id:
                    data[KEY_TASKS][KEY_REPETITIVE_TASK].pop(index)
                    if str(task_id) in data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK]:
                        del (data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][str(task_id)])

        self._save_calendar(contents=data, filename=calendar_id)

    def update_task_day(self, calendar_id: str, year_str: str, month_str: str, day_str: str, task_id: int,
                        new_day_str: str) -> None:
        data = self.load_calendar(calendar_id)

        task_to_update = None
        for index, task in enumerate(data[KEY_TASKS][KEY_NORMAL_TASK][year_str][month_str][day_str]):
            if task["id"] == task_id:
                task_to_update = data[KEY_TASKS][KEY_NORMAL_TASK][year_str][month_str][day_str].pop(index)

        if task_to_update is None:
            return

        if new_day_str not in data[KEY_TASKS][KEY_NORMAL_TASK][year_str][month_str]:
            data[KEY_TASKS][KEY_NORMAL_TASK][year_str][month_str][new_day_str] = []
        data[KEY_TASKS][KEY_NORMAL_TASK][year_str][month_str][new_day_str].append(task_to_update)

        self._save_calendar(contents=data, filename=calendar_id)

    def create_task(self, calendar_id: str, year: Optional[int], month: Optional[int], day: Optional[int], title: str,
                    is_all_day: bool, due_time: str, details: str, color: str, has_repetition: bool,
                    repetition_type: str, repetition_subtype: str, repetition_value: int) -> bool:
        details = details if len(details) > 0 else "&nbsp;"
        data = self.load_calendar(calendar_id)

        new_task = {
            "id": int(time.time()),
            "color": color,
            "due_time": due_time,
            "is_all_day": is_all_day,
            "title": title,
            "details": details
        }
        if has_repetition:
            if repetition_type == self.REPETITION_SUBTYPE_MONTH_DAY and repetition_value == 0:
                return False
            new_task["repetition_type"] = repetition_type
            new_task["repetition_subtype"] = repetition_subtype
            new_task[KEY_REPEAT_VALUE] = repetition_value
            data[KEY_TASKS][KEY_REPETITIVE_TASK].append(new_task)
        else:
            if year is None or month is None or day is None:
                return False
            year_str = str(year)
            month_str = str(month)
            day_str = str(day)
            if year_str not in data[KEY_TASKS][KEY_NORMAL_TASK]:
                data[KEY_TASKS][KEY_NORMAL_TASK][year_str] = {}
            if month_str not in data[KEY_TASKS][KEY_NORMAL_TASK][year_str]:
                data[KEY_TASKS][KEY_NORMAL_TASK][year_str][month_str] = {}
            if day_str not in data[KEY_TASKS][KEY_NORMAL_TASK][year_str][month_str]:
                data[KEY_TASKS][KEY_NORMAL_TASK][year_str][month_str][day_str] = []
            data[KEY_TASKS][KEY_NORMAL_TASK][year_str][month_str][day_str].append(new_task)

        self._save_calendar(contents=data, filename=calendar_id)
        return True

    # create customized repeated tasks
    def create_customized_task(self, calendar_id: str, year: Optional[int], month: Optional[int], day: Optional[int],
                               title: str,
                               is_all_day: bool, due_time: str, details: str, color: str, has_repetition: bool,
                               repetition_type: str, repetition_value: int, customized_total_repeat: int) -> bool:
        details = details if len(details) > 0 else "&nbsp;"
        data = self.load_calendar(calendar_id)

        new_task = {
            "id": int(time.time()),
            "color": color,
            "due_time": due_time,
            "is_all_day": is_all_day,
            "title": title,
            "details": details
        }
        if has_repetition:
            # if repetition_type == self.REPETITION_SUBTYPE_MONTH_DAY and repetition_value == 0:
            #     return False
            new_task["repetition_type"] = repetition_type
            # new_task["repetition_subtype"] = repetition_subtype
            new_task[KEY_REPEAT_VALUE] = repetition_value

            new_task[KEY_REPEAT_TOTAL] = customized_total_repeat
            new_task[KEY_REPEAT_BEGIN] = str(year) + "-" + str(month) + "-" + str(day)
            data[KEY_TASKS][KEY_REPETITIVE_TASK].append(new_task)
        else:
            if year is None or month is None or day is None:
                return False
            year_str = str(year)
            month_str = str(month)
            day_str = str(day)
            if year_str not in data[KEY_TASKS][KEY_NORMAL_TASK]:
                data[KEY_TASKS][KEY_NORMAL_TASK][year_str] = {}
            if month_str not in data[KEY_TASKS][KEY_NORMAL_TASK][year_str]:
                data[KEY_TASKS][KEY_NORMAL_TASK][year_str][month_str] = {}
            if day_str not in data[KEY_TASKS][KEY_NORMAL_TASK][year_str][month_str]:
                data[KEY_TASKS][KEY_NORMAL_TASK][year_str][month_str][day_str] = []
            data[KEY_TASKS][KEY_NORMAL_TASK][year_str][month_str][day_str].append(new_task)

        self._save_calendar(contents=data, filename=calendar_id)
        return True

    def hide_repetition_task_instance(self, calendar_id: str, year_str: str, month_str: str, day_str: str,
                                      task_id_str: str) -> None:
        data = self.load_calendar(calendar_id)

        if task_id_str not in data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK]:
            data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][task_id_str] = {}
        if year_str not in data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][task_id_str]:
            data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][task_id_str][year_str] = {}
        if month_str not in data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][task_id_str][year_str]:
            data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][task_id_str][year_str][month_str] = {}
        data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][task_id_str][year_str][month_str][day_str] = True

        self._save_calendar(contents=data, filename=calendar_id)

    def _repetitive_tasks_from_calendar(
            self, year: int, month: int, month_days: List, calendar_id: Optional[str] = None, data: Dict = None
    ) -> Dict:
        if data is None:
            if calendar_id is None:
                raise ValueError("Need to provide either calendar_id or loaded data")
            else:
                data = self.load_calendar(calendar_id)

        repetitive_tasks = {}  # type: Dict
        year_str = str(year)
        month_str = str(month)

        if KEY_TASKS not in data.keys():
            ValueError("Incomplete data for calendar id '{}'".format(calendar_id))
        if KEY_REPETITIVE_TASK not in data[KEY_TASKS].keys():
            ValueError("Incomplete data for calendar id '{}'".format(calendar_id))

        for task in data[KEY_TASKS][KEY_REPETITIVE_TASK]:
            id_str = str(task["id"])

            for week in month_days:
                for weekday, day in enumerate(week):
                    if day == 0:
                        continue

                    total_repeats = str(task[KEY_REPEAT_TOTAL])
                    repeat_freq = str(task[KEY_REPEAT_VALUE])
                    this_day_date = datetime.date(year, month, day)
                    begin_year, begin_month, begin_day = str(task[KEY_REPEAT_BEGIN]).split("-")
                    begin_day_date = datetime.date(int(begin_year), int(begin_month), int(begin_day))
                    days_range_timedelta = this_day_date - begin_day_date

                    # if this day before the begin day, pass
                    if int(days_range_timedelta.days) < 0:
                        continue

                    if task["repetition_type"] == self.REPETITION_TYPE_WEEKLY:
                        if self._is_repetition_hidden_for_day(data, id_str, year_str, month_str, str(day)):
                            continue
                        # as this is weekly, so should be
                        if (int(days_range_timedelta.days) % (int(repeat_freq) * 7) == 0) and (
                                int(days_range_timedelta.days) / (int(repeat_freq) * 7) < int(total_repeats)):
                            task_with_count = deepcopy(task)
                            task_with_count["title"] = task["title"] + "(" + str(
                                int(days_range_timedelta.days / (int(repeat_freq) * 7) + 1)) \
                                                       + "/" + total_repeats + ")"
                            self.add_task_to_list(repetitive_tasks, day, task_with_count)
                    elif task["repetition_type"] == self.REPETITION_TYPE_MONTHLY:
                        if self._is_repetition_hidden(data, id_str, year_str, month_str):
                            continue
                        if day == int(begin_day) \
                                and (month + (12 * (year - int(begin_year)))) >= int(begin_month) \
                                and year >= int(begin_year):
                            if (month - int(begin_month) + (12 * (year - int(begin_year)))) % int(repeat_freq) == 0 \
                                    and (month - int(begin_month) + (12 * (year - int(begin_year)))) / int(repeat_freq) \
                                    < int(total_repeats):
                                task_with_count = deepcopy(task)
                                task_with_count["title"] = task["title"] + "(" + str(
                                    int((month + (12 * (year - int(begin_year)))) - int(begin_month) + 1)) + "/" + total_repeats + ")"
                                self.add_task_to_list(repetitive_tasks, day, task_with_count)
                    elif task["repetition_type"] == self.REPETITION_TYPE_CUSTOMIZED:
                        if self._is_repetition_hidden_for_day(data, id_str, year_str, month_str, str(day)):
                            continue
                        if (KEY_REPEAT_TOTAL in task.keys()) and (KEY_REPEAT_BEGIN in task.keys()):
                            if (int(days_range_timedelta.days) % int(repeat_freq) == 0) and (
                                    int(days_range_timedelta.days) / int(repeat_freq) < int(total_repeats)):
                                task_with_count = deepcopy(task)
                                task_with_count["title"] = task["title"] + "(" + str(
                                    int(days_range_timedelta.days / int(repeat_freq) + 1)) \
                                                           + "/" + total_repeats + ")"
                                self.add_task_to_list(repetitive_tasks, day, task_with_count)
        return repetitive_tasks

    @staticmethod
    def _is_repetition_hidden_for_day(data: Dict, id_str: str, year_str: str, month_str: str, day_str: str) -> bool:
        if id_str in data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK]:
            if (year_str in data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][id_str] and
                    month_str in data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][id_str][year_str] and
                    day_str in data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][id_str][year_str][month_str]):
                return True
        return False

    @staticmethod
    def _is_repetition_hidden(data: Dict, id_str: str, year_str: str, month_str: str) -> bool:
        if id_str in data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK]:
            if (year_str in data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][id_str] and
                    month_str in data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][id_str][year_str]):
                return True
        return False

    def _save_calendar(self, contents: Dict, filename: str) -> None:
        self._clear_empty_entries(data=contents)
        self._clear_past_hidden_entries(data=contents)
        with open(os.path.join(".", self.data_folder, "{}.json".format(filename)), "w+") as file:
            json.dump(contents, file)

    @staticmethod
    def _clear_empty_entries(data: Dict) -> None:
        years_to_delete = []

        for year in data[KEY_TASKS][KEY_NORMAL_TASK]:
            months_to_delete = []
            for month in data[KEY_TASKS][KEY_NORMAL_TASK][year]:
                days_to_delete = []
                for day in data[KEY_TASKS][KEY_NORMAL_TASK][year][month]:
                    if len(data[KEY_TASKS][KEY_NORMAL_TASK][year][month][day]) == 0:
                        days_to_delete.append(day)
                for day in days_to_delete:
                    del (data[KEY_TASKS][KEY_NORMAL_TASK][year][month][day])
                if len(data[KEY_TASKS][KEY_NORMAL_TASK][year][month]) == 0:
                    months_to_delete.append(month)
            for month in months_to_delete:
                del (data[KEY_TASKS][KEY_NORMAL_TASK][year][month])
            if len(data[KEY_TASKS][KEY_NORMAL_TASK][year]) == 0:
                years_to_delete.append(year)

        for year in years_to_delete:
            del (data[KEY_TASKS][KEY_NORMAL_TASK][year])

    @staticmethod
    def _clear_past_hidden_entries(data: Dict) -> None:
        _, current_month, current_year = GregorianCalendar.current_date()
        task_ids_to_delete = []

        for task_id in data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK]:
            years_to_delete = []
            for year in data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][task_id]:
                months_to_delete = []
                for month in data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][task_id][year]:
                    if (int(year) < current_year) or (int(year) == current_year and int(month) < current_month):
                        months_to_delete.append(month)
                for month in months_to_delete:
                    del (data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][task_id][year][month])
                if len(data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][task_id][year]) == 0:
                    years_to_delete.append(year)
            for year in years_to_delete:
                del (data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][task_id][year])
            if len(data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][task_id]) == 0:
                task_ids_to_delete.append(task_id)

        for task_id in task_ids_to_delete:
            del (data[KEY_TASKS][KEY_REPETITIVE_HIDDEN_TASK][task_id])
