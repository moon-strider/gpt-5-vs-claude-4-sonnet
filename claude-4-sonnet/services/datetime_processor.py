import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

GMT_TIMEZONE = timezone.utc


@dataclass
class TaskOccurrence:
    date: str
    time: str
    datetime_obj: datetime


class DateTimeProcessor:
    def __init__(self):
        self.gmt_timezone = GMT_TIMEZONE
    
    def validate_date_time(self, date_str: Optional[str], time_str: Optional[str]) -> Dict[str, Any]:
        validation_result = {
            "valid": True,
            "error": None,
            "date": date_str,
            "time": time_str
        }
        
        if date_str:
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
                if parsed_date.month > 12 or parsed_date.day > 31:
                    validation_result["valid"] = False
                    validation_result["error"] = f"Invalid date detected: {date_str}. Please use a valid date format."
                    return validation_result
                
                if parsed_date.month == 2 and parsed_date.day > 29:
                    validation_result["valid"] = False
                    validation_result["error"] = f"Invalid date detected: {date_str}. Please use a valid date format."
                    return validation_result
                    
                if parsed_date.month == 2 and parsed_date.day == 29 and not self._is_leap_year(parsed_date.year):
                    validation_result["valid"] = False
                    validation_result["error"] = f"Invalid date detected: {date_str}. Please use a valid date format."
                    return validation_result
                
                if parsed_date.month in [4, 6, 9, 11] and parsed_date.day > 30:
                    validation_result["valid"] = False
                    validation_result["error"] = f"Invalid date detected: {date_str}. Please use a valid date format."
                    return validation_result
                    
            except ValueError:
                validation_result["valid"] = False
                validation_result["error"] = f"Invalid date detected: {date_str}. Please use a valid date format."
                return validation_result
        
        if time_str:
            try:
                time_parts = time_str.split(":")
                if len(time_parts) != 2:
                    raise ValueError("Invalid time format")
                
                hour, minute = int(time_parts[0]), int(time_parts[1])
                
                if hour < 0 or hour > 23:
                    validation_result["valid"] = False
                    validation_result["error"] = f"Invalid time detected: {time_str}. Please use 24-hour format (HH:MM)."
                    return validation_result
                
                if minute < 0 or minute > 59:
                    validation_result["valid"] = False
                    validation_result["error"] = f"Invalid time detected: {time_str}. Please use 24-hour format (HH:MM)."
                    return validation_result
                    
            except ValueError:
                validation_result["valid"] = False
                validation_result["error"] = f"Invalid time detected: {time_str}. Please use 24-hour format (HH:MM)."
                return validation_result
        
        return validation_result
    
    def _is_leap_year(self, year: int) -> bool:
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    
    async def get_next_occurrences(self, task: Dict[str, Any], limit: int = 3) -> List[str]:
        """Get next occurrences for a task as formatted strings"""
        date_str = task.get("date")
        time_str = task.get("time")
        recurrence = task.get("recurrence")
        
        occurrences = self.get_next_occurrences_objects(date_str, time_str, recurrence, limit)
        
        return [f"{occ.date} at {occ.time}" for occ in occurrences]
    
    def get_next_occurrences_objects(self, date_str: Optional[str], time_str: Optional[str], 
                           recurrence: Optional[str], limit: int = 3) -> List[TaskOccurrence]:
        now = datetime.now(self.gmt_timezone)
        occurrences = []
        
        default_time = time_str or "09:00"
        
        try:
            if date_str and recurrence in [None, "none"]:
                task_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=self.gmt_timezone)
                if default_time:
                    time_parts = default_time.split(":")
                    task_date = task_date.replace(hour=int(time_parts[0]), minute=int(time_parts[1]))
                
                if task_date > now:
                    occurrences.append(TaskOccurrence(
                        date=task_date.strftime("%b %d, %Y"),
                        time=f"{task_date.strftime('%H:%M')} GMT",
                        datetime_obj=task_date
                    ))
            
            elif recurrence and recurrence != "none":
                occurrences.extend(self._calculate_recurring_occurrences(
                    date_str, default_time, recurrence, now, limit
                ))
            
            elif not date_str and not recurrence:
                default_date = now + timedelta(days=1)
                if default_time:
                    time_parts = default_time.split(":")
                    default_date = default_date.replace(hour=int(time_parts[0]), minute=int(time_parts[1]))
                
                occurrences.append(TaskOccurrence(
                    date=default_date.strftime("%b %d, %Y"),
                    time=f"{default_date.strftime('%H:%M')} GMT",
                    datetime_obj=default_date
                ))
            
        except Exception as e:
            logger.error(f"Error calculating occurrences: {e}")
            return []
        
        return occurrences[:limit]
    
    def _calculate_recurring_occurrences(self, date_str: Optional[str], time_str: str, 
                                       recurrence: str, now: datetime, limit: int) -> List[TaskOccurrence]:
        occurrences = []
        
        try:
            time_parts = time_str.split(":")
            hour, minute = int(time_parts[0]), int(time_parts[1])
            
            if date_str:
                start_date = datetime.strptime(date_str, "%Y-%m-%d").replace(
                    hour=hour, minute=minute, tzinfo=self.gmt_timezone
                )
            else:
                start_date = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if start_date <= now:
                start_date = self._get_next_occurrence_date(start_date, recurrence, now)
            
            current_date = start_date
            count = 0
            
            while count < limit:
                occurrences.append(TaskOccurrence(
                    date=current_date.strftime("%b %d, %Y"),
                    time=f"{current_date.strftime('%H:%M')} GMT",
                    datetime_obj=current_date
                ))
                
                current_date = self._get_next_occurrence_date(current_date, recurrence, current_date)
                count += 1
                
        except Exception as e:
            logger.error(f"Error calculating recurring occurrences: {e}")
            
        return occurrences
    
    def _get_next_occurrence_date(self, current_date: datetime, recurrence: str, reference_date: datetime) -> datetime:
        if recurrence == "daily":
            return current_date + timedelta(days=1)
        elif recurrence == "weekly":
            return current_date + timedelta(weeks=1)
        elif recurrence.startswith("weekly_"):
            return self._get_next_weekday_occurrence(current_date, recurrence)
        elif recurrence == "monthly":
            if current_date.month == 12:
                next_month = current_date.replace(year=current_date.year + 1, month=1)
            else:
                next_month = current_date.replace(month=current_date.month + 1)
            
            try:
                return next_month
            except ValueError:
                return next_month.replace(day=28)
        elif recurrence == "yearly":
            try:
                return current_date.replace(year=current_date.year + 1)
            except ValueError:
                return current_date.replace(year=current_date.year + 1, month=2, day=28)
        else:
            return current_date + timedelta(days=1)
    
    def _get_next_weekday_occurrence(self, current_date: datetime, recurrence: str) -> datetime:
        try:
            weekdays_str = recurrence.replace("weekly_", "")
            weekdays = [int(d) for d in weekdays_str.split("_")]
            
            current_weekday = current_date.weekday()
            days_ahead = None
            
            for weekday in sorted(weekdays):
                if weekday > current_weekday:
                    days_ahead = weekday - current_weekday
                    break
            
            if days_ahead is None:
                days_ahead = (7 - current_weekday) + min(weekdays)
            
            return current_date + timedelta(days=days_ahead)
        except:
            return current_date + timedelta(days=1)


datetime_processor = DateTimeProcessor()