import sys
import arrow
from collections import deque
from bs4 import BeautifulSoup
from ics import Calendar, Event

# Requires lxml module

USAGE = (
    f"Usage: python {sys.argv[0]} [-m YYYY-MM] <input html 1> "
    "[<input html 2> ...] <output ics>"
)


def main():
    """Converts one or more IVU schedule html-files into a single ics calender
    file."""
    ivu_htmls, output_ics, date_string = parse_arguments()
    events = ivu_to_events(*ivu_htmls)
    if date_string:
        events = purge_events(events, date_string)
    write_to_ics(events, output_ics)


def parse_arguments():
    """Parses command line arguments. Returns a list of input IVU htmls,
    output ics (string) and date string (None if -m flag not present).
    Raises SystemExit if too few arguments or if the output ics lacks suffix
    .ics"""
    args = deque(sys.argv[1:])  # sys.argv[0] is the name of this script
    if len(args) < 2:
        raise SystemExit(USAGE)
    if args[0] == "-m":
        args.popleft()
        date_string = args.popleft()
        if len(args) < 2:
            raise SystemExit(USAGE)
    else:
        date_string = None
    output_ics = args.pop()
    if not output_ics.endswith(".ics"):
        raise SystemExit(f'<output ics> must end in ".ics". {USAGE}')
    ivu_htmls = args
    return ivu_htmls, output_ics, date_string


def ivu_to_events(*ivu_htmls):
    """Returns a set of ics Event objects"""
    events = set()

    for ivu_html in ivu_htmls:
        with open(ivu_html, "r") as site:
            soup = BeautifulSoup(site, "lxml")

        days = soup(class_="day")

        for day in days:
            a_day = day.find(class_="allocation-day")
            if not a_day:
                continue
            date = a_day["data-date"]

            title = day.find(class_="title-text")
            if not title:  # if empty day
                continue
            title = title.string.strip()  # has leading spaces

            e = Event()
            e.name = title

            begin = day.find(class_="time begin")
            end = day.find(class_="time end")
            if begin:  # work day
                # start with end time in case dygnsöverskridande tur
                if end.string.endswith("+") or "00:00" in end.string:
                    e.end = f'{date} {end.string.strip().strip("+")}'
                    e.end = e.end.shift(days=+1)  # see 'arrow' docs
                else:
                    e.end = f"{date} {end.string.strip()}"
                e.begin = f"{date} {begin.string.strip()}"
                e.begin = e.begin.replace(tzinfo="Europe/Stockholm")
                e.end = e.end.replace(tzinfo="Europe/Stockholm")
            else:  # free day
                e.begin = date
                e.make_all_day()

            events.add(e)

    return events


def purge_events(events, date_string):
    """For now, assumes date_string is a month. Returns a purged set of ics
    Event objects from only the specified month"""
    try:
        floor, ceiling = arrow.get(date_string).span("month")
    except arrow.parser.ParserError:
        raise SystemExit(USAGE)
    events = {event for event in events if floor <= event.begin < ceiling}
    return events


def write_to_ics(events, output_ics):
    """Writes events to .ics file"""
    c = Calendar(events=events)
    with open(output_ics, "w") as fout:
        fout.write(c.serialize())
    print(f"{len(events)} event(s) written to {output_ics}.")


if __name__ == "__main__":
    main()
