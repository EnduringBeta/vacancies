from datetime import date, timedelta
from typing import TypedDict, AnyStr, List, Any, Tuple, Optional
import time

"""
# General approach & Thoughts

I started with a brute force approach to get a baseline understanding of the loop
and structure. Then, after realizing how N+1 can build upon N's data, I added a
layer to use previously-calculated bundles to compare against instead of vacancies.
A hypothesis I believe to be true is that vacancy length of N cannot be greater than N-1,
and in fact that N+1 must be based on an existing N bundle.

The next significant adjustment I needed to make was to check for matching bundle
members and not add duplicates to the longest bundle lists.

I needed to change all dates to advance to 2025 from 2024, and I changed a leap day
entry to 28 Feb. This changed some results by +/- 1, but also I don't know when the
example results were calculated to know what was past/present at that time and
thus excluded/included.

# Results

Here are my results compared to the examples, which have differences I didn't
have time to fully explore right or wrong:

* Trial 0 - extra N=4 of 13 days
* Trial 1 - extra N=4,5 of 21, 17 days
* Trial 2 - different N=3,4
* Trial 3 - different N=3, extra N=6 of 22 days
* Trial 4 - missing N=5 of 52 days
* Trial 5 - extra N=4 of 20 days
* Trial 6 - different N=3,5
* Trial 7 - extra N=4

# Big O

n * ((n) + n*(3n/2) + n*(#)) -> n^2 * (1 + 3n/2 + #) -> O(n^3)

A quick check with an LLM says that O(n * log(n)) is possible, but I couldn't confirm
its implementation.

# remove_vacancies()

I didn't have time to implement this, but there are definitely optimizations available
instead of running the calculation from scratch. Removing the N = 1 entry for this bed ID
if its dates match would be simple, and then for N = 2+, we could check if the bundle
contains the vacancy and re-run N+ from there. I expect there may be further improvements.

This assumes the booking is for the entirety of a vacancy and not a sub-set, which is
actually more realistic but has significantly more complexity.

# add_vacancies()

I didn't have time to implement this, but there are definitely optimizations available
instead of running the calculation from scratch. Updating the N = 1 entry for this bed ID
would be simple, and then for N = 2+, we could check if the longest bundle lists would
be affected by the additional vacancy. If not, we can stop.

This assumes the booking is for the entirety of a vacancy and not a sub-set, which is
actually more realistic but has significantly more complexity.
"""

remove_expired_vacancies = True
combine_adjacent_vacancies = True
print_results = True

class Vacancy(TypedDict):
    bed_id: AnyStr  # unique bed id
    start_date: date  # earliest available booking date
    end_date: date  # latest available booking date for the set of contiguous dates beginning on start_date


class VacancyBundle(TypedDict):
    size: int  # the number of vacancies in this bundle
    start_date: date  # start of the largest date window that of overlaps across all vacancies in this bundle
    end_date: date  # end of the largest date window that of overlaps across all vacancies in this bundle
    members: List[Vacancy]  # list of overlapping vacancies in this bundle


def calc_vacancy_bundles(vacancies: List[Vacancy]) -> List[VacancyBundle]:
    print("Calculating vacancy bundles...")

    vacancy_bundles = []

    # Check for empty list
    if not vacancies:
        return vacancy_bundles
    
    if combine_adjacent_vacancies:
        vacancies = _combine_adjacent_vacancies(vacancies)

    today = date.today()

    # Remove expired vacancies, sort by start date, and calculate "n"
    # TODO: could also adjust all vacancies to have start date of today if in the past
    orig_num_vacancies = len(vacancies)
    if remove_expired_vacancies:
        vacancies = [vacancy for vacancy in vacancies if vacancy["end_date"] >= today]
    
    num_vacancies = len(vacancies)
    if orig_num_vacancies > num_vacancies:
        print("Removed", orig_num_vacancies - num_vacancies, "expired vacancies")

    vacancies.sort(key=lambda x: x["start_date"])

    longest_bundles: List[VacancyBundle] = []
    previous_longest_bundles: List[VacancyBundle] = []

    # For each "n" value (# simultaneous travelers wanting beds)
    for n in range(1, num_vacancies + 1):
        print("\nComputing vacancy bundles for n =", n, "\n")

        delta = timedelta()

        if n == 1:
            # If "n" == 1, create bundles immediately from existing vacancies
            # TODO: not DRY; copied from another section
            for vacancy in vacancies:
                new_delta = _get_delta((vacancy["start_date"], vacancy["end_date"]))
                if new_delta >= delta:
                    if new_delta > delta:
                        delta = new_delta
                        longest_bundles = []
                    
                    print("Found new n =", n, "long bundle with days:", delta.days)
                    longest_bundles.append(VacancyBundle(
                        size=n,
                        members=[vacancy],
                        start_date=vacancy["start_date"],
                        end_date=vacancy["end_date"]
                    ))
        else:
            # Check all overlap windows
            for i in range(num_vacancies):
                print("Checking vacancy", i)

                vacancy1 = vacancies[i]

                comparing_to_bundles = n > 2

                # If "n" == 1, compare against other vacancies
                # If "n" > 1, longest bundles will be calculated, so compare
                # against those to find the longest windows for "n"
                # Both of these classes have "start_date" and "end_date"
                comparators = []
                if comparing_to_bundles:
                    # If no bundles, then no windows exist and won't for higher "n",
                    # so return (this is checked in previous loop at the end, so this
                    # shouldn't happen here)
                    if not previous_longest_bundles:
                        return vacancy_bundles
                    comparators = previous_longest_bundles
                else:
                    comparators = vacancies[i+1:]

                # Compare with other vacancies or "n-1" longest bundle windows
                for comparator in comparators:
                    if comparing_to_bundles:
                        # Check if vacancy bed ID is already in bundle, and skip if so
                        if _does_bundle_contain_bed_id(comparator, vacancy1):
                            print("Skipping vacancy", vacancy1["bed_id"], "already in bundle")
                            continue

                    print("Comparing to", comparator["start_date"])

                    window = _get_overlap_window(
                        vacancy1,
                        (comparator["start_date"], comparator["end_date"])
                    )
                    if window is None:
                        continue
                    
                    new_delta = _get_delta(window)
                    if new_delta >= delta:
                        if new_delta > delta:
                            delta = new_delta
                            longest_bundles = []
                        
                        # If second item is bundle, get members; otherwise it should be a vacancy
                        members = [vacancy1] + comparator.get("members", [comparator])

                        bundle = VacancyBundle(
                            size=n,
                            members=members,
                            start_date=window[0],
                            end_date=window[1]
                        )

                        if comparing_to_bundles:
                            # Check that bed_id & dates list doesn't match (duplicate)
                            if _are_bundle_members_present(longest_bundles, bundle):
                                print("Skipping bundle with same beds and dates")
                                continue
                        
                        print("Found new n =", n, "long bundle with days:", delta.days)
                        longest_bundles.append(VacancyBundle(
                            size=n,
                            members=members,
                            start_date=window[0],
                            end_date=window[1]
                        ))
                    
                    # Artificial delay for debugging
                    #time.sleep(0.5)
        
        # If no windows found for "n", no further windows will be found
        if not longest_bundles:
            print("\nNo n =", n, "bundles found\n")
            return vacancy_bundles
        else:
            print("\nLongest n =", n, "bundles found:", len(longest_bundles))
            print(longest_bundles)

        # After looping to find longest bundles, sort by start date
        # and keep first one as "official" answer
        longest_bundles.sort(key=lambda x: x["start_date"])
        vacancy_bundles.append(longest_bundles[0])

        # Reset list for next "n"
        previous_longest_bundles = longest_bundles
        longest_bundles = []

        print("\nFinal n =", n, "bundle:\n")
        print(vacancy_bundles[n-1])

    return vacancy_bundles

# Find the overlap window between two vacancies or a vacancy and
# an existing bundle window, if any
def _get_overlap_window(vacancy1: Vacancy, window: Tuple[date, date]) -> Optional[Tuple[date, date]]:
    window_start_date, window_end_date = window
    # If no window, return None
    if vacancy1["start_date"] > window_end_date \
        or window_start_date > vacancy1["end_date"]:
            return None
    
    start_window = max(vacancy1["start_date"], window_start_date)
    end_window = min(vacancy1["end_date"], window_end_date)
    return start_window, end_window

def _get_delta(date_range: Tuple[date, date]) -> timedelta:
    start_date, end_date = date_range
    return end_date - start_date

# It's possible vacancy can be for the same bed ID but a different window, but that
# by definition will not overlap with the existing vacancy with that bed ID in a
# bundle, assuming combine_adjacent_vacancies is True and executed
def _does_bundle_contain_bed_id(bundle: VacancyBundle, vacancy: Vacancy) -> bool:
    for v in bundle["members"]:
        if vacancy["bed_id"] == v["bed_id"]:
            return True
    return False

# This originally only checked bed IDs, but another vacancy with a bed ID in the bundle
# but a different window can still be valid and different (not "present")
def _are_bundle_members_present(bundles: List[VacancyBundle], bundle: VacancyBundle) -> bool:
    for b in bundles:
        if len(b["members"]) != len(bundle["members"]):
            continue
        
        if all(any(_are_vacancies_equal(v1, v2) for v2 in b["members"])
               for v1 in bundle["members"]):
            return True
    
    return False

def _are_vacancies_equal(vacancy1: Vacancy, vacancy2: Vacancy) -> bool:
    return (vacancy1["bed_id"] == vacancy2["bed_id"] and
            vacancy1["start_date"] == vacancy2["start_date"] and
            vacancy1["end_date"] == vacancy2["end_date"])

# This always keeps the first adjacent vacancy, even if it had the later dates,
# and it reorders the input list, but it's sorted later outside this function anyway
def _combine_adjacent_vacancies(vacancies: List[Vacancy]) -> List[Vacancy]:
    combined_vacancies = vacancies
    
    # Get all bed IDs
    bed_ids = {vacancy["bed_id"] for vacancy in combined_vacancies}
    
    # Process each instance of multiple same bed IDs
    for bed_id in bed_ids:
        # Get all vacancies with this bed ID
        same_bed_vacancies = [vacancy for vacancy in combined_vacancies if vacancy["bed_id"] == bed_id]

        # If just 1 vacancy (common), move on
        if len(same_bed_vacancies) == 1:
            continue

        print("Multiple vacancies for bed ID", bed_id)

        # Sort by start date
        same_bed_vacancies.sort(key=lambda x: x["start_date"])
        
        # Check if any are adjacent
        for i in range(len(same_bed_vacancies) - 1):
            if same_bed_vacancies[i]["end_date"] == same_bed_vacancies[i + 1]["start_date"]:
                # Combine into one vacancy by expanding current vacancy's end date
                # and removing time-adjacent vacancy
                same_bed_vacancies[i]["end_date"] = max(same_bed_vacancies[i]["end_date"], same_bed_vacancies[i + 1]["end_date"])
                del same_bed_vacancies[i + 1]
                print("Found adjacent vacancies and combined!")

        # Replace original vacancies with combined ones
        combined_vacancies = [
            vacancy for vacancy in combined_vacancies if vacancy["bed_id"] != bed_id
        ] + same_bed_vacancies

    return combined_vacancies

"""
Extra credit for fun
"""


class Reservation(TypedDict):
    reservation_id: AnyStr  # unique reservation id
    start_date: date  # earliest available booking date
    end_date: date  # latest available booking date for the set of contiguous dates beginning on start_date
    bed_ids: List[AnyStr]

# Cesar said to add `vacancy_bundles` because "We're just giving you explicit access to the prior vacancy bundles you may have calculated"

def remove_vacancies(booking: Reservation, vacancies, vacancy_bundles, **kwargs) -> Tuple[List[Vacancy], List[VacancyBundle], Any]:
    # Awesome, looks like we got a booking! Now we have to adjust the vacancy bundles as well as their
    # underlying Vacancies, Bundles and any other data structures we want to propagate forward.
    # we could just re-calculate the vacancy bundles from scratch but can you think of a better way?
    raise NotImplementedError


def add_vacancies(cancellation: Reservation, vacancies, vacancy_bundles, **kwargs) -> Tuple[List[Vacancy], List[VacancyBundle], Any]:
    # Oh oh, looks like we had a reservation cancellation, and now we have to adjust
    # the existing Vacancies, Bundles and any other data structures we want to propagate forward.
    # we could just re-calculate the vacancy bundles from scratch but can you think of a better way?
    raise NotImplementedError

# Testing Zone

# From example_solutions.txt (changed all 2024 to 2025 and changed 1 29 Feb date in trial 4 to 28 Feb)
# Compare against `SOLUTION:` data there
trial_empty = []
trial_0 = [(date(2025, 3, 2), date(2025, 6, 8), 3), (date(2025, 3, 15), date(2025, 12, 21), 0), (date(2025, 4, 27), date(2025, 6, 19), 6), (date(2025, 6, 16), date(2025, 9, 10), 7), (date(2025, 6, 30), date(2025, 8, 11), 1), (date(2025, 7, 29), date(2025, 9, 25), 5), (date(2025, 9, 10), date(2025, 11, 8), 4), (date(2025, 11, 16), date(2025, 12, 26), 2)]
trial_1 = [(date(2025, 1, 18), date(2025, 6, 30), 7), (date(2025, 6, 1), date(2025, 8, 27), 3), (date(2025, 6, 12), date(2025, 8, 23), 4), (date(2025, 6, 28), date(2025, 12, 24), 6), (date(2025, 8, 4), date(2025, 11, 15), 0), (date(2025, 8, 6), date(2025, 10, 8), 5), (date(2025, 9, 29), date(2025, 11, 28), 2), (date(2025, 11, 19), date(2025, 12, 25), 1)]
trial_2 = [(date(2025, 2, 5), date(2025, 5, 7), 6), (date(2025, 2, 16), date(2025, 9, 20), 5), (date(2025, 2, 19), date(2025, 11, 23), 4), (date(2025, 4, 8), date(2025, 7, 4), 3), (date(2025, 4, 25), date(2025, 9, 6), 1), (date(2025, 4, 29), date(2025, 7, 13), 2), (date(2025, 5, 25), date(2025, 11, 28), 0), (date(2025, 5, 26), date(2025, 12, 13), 7)]
trial_3 = [(date(2025, 3, 13), date(2025, 12, 18), 1), (date(2025, 4, 3), date(2025, 10, 6), 5), (date(2025, 4, 24), date(2025, 9, 24), 4), (date(2025, 5, 21), date(2025, 12, 24), 7), (date(2025, 8, 22), date(2025, 10, 7), 3), (date(2025, 9, 2), date(2025, 10, 17), 0), (date(2025, 10, 21), date(2025, 12, 11), 6), (date(2025, 10, 25), date(2025, 12, 10), 2)]
trial_4 = [(date(2025, 1, 11), date(2025, 3, 28), 1), (date(2025, 1, 29), date(2025, 12, 2), 7), (date(2025, 2, 24), date(2025, 12, 29), 4), (date(2025, 2, 28), date(2025, 11, 26), 2), (date(2025, 5, 1), date(2025, 7, 19), 3), (date(2025, 8, 21), date(2025, 10, 17), 5), (date(2025, 8, 26), date(2025, 10, 23), 0), (date(2025, 10, 6), date(2025, 11, 29), 6)]
trial_5 = [(date(2025, 3, 27), date(2025, 5, 20), 6), (date(2025, 4, 23), date(2025, 9, 12), 4), (date(2025, 7, 23), date(2025, 10, 16), 1), (date(2025, 7, 29), date(2025, 12, 15), 2), (date(2025, 8, 23), date(2025, 10, 29), 3), (date(2025, 10, 12), date(2025, 12, 12), 7), (date(2025, 11, 24), date(2025, 12, 31), 5), (date(2025, 11, 28), date(2025, 1, 1), 0)]
trial_6 = [(date(2025, 1, 22), date(2025, 8, 19), 2), (date(2025, 4, 20), date(2025, 8, 4), 5), (date(2025, 4, 22), date(2025, 12, 7), 7), (date(2025, 6, 1), date(2025, 7, 19), 3), (date(2025, 6, 14), date(2025, 10, 17), 6), (date(2025, 7, 17), date(2025, 9, 12), 4), (date(2025, 8, 7), date(2025, 11, 29), 0), (date(2025, 8, 22), date(2025, 12, 10), 1)]
trial_7 = [(date(2025, 1, 18), date(2025, 5, 19), 0), (date(2025, 2, 6), date(2025, 9, 5), 6), (date(2025, 3, 27), date(2025, 11, 29), 3), (date(2025, 5, 7), date(2025, 6, 18), 5), (date(2025, 9, 23), date(2025, 11, 10), 2), (date(2025, 10, 15), date(2025, 12, 18), 7), (date(2025, 11, 11), date(2025, 12, 29), 1), (date(2025, 11, 14), date(2025, 12, 24), 4)]

def _tuple_list_to_vacancies(tup_list: List[Tuple[date, date, int]]) -> List[Vacancy]:
    return [_tuple_to_vacancy(tup) for tup in tup_list]

def _tuple_to_vacancy(tup: Tuple[date, date, int]) -> Vacancy:
    return {
        "bed_id": tup[2],
        "start_date": tup[0],
        "end_date": tup[1]
    }

def _print_bundles(bundles: List[VacancyBundle]) -> None:
    for bundle in bundles:
        print("Bundle", bundle["size"], "[", bundle["start_date"], "->", bundle["end_date"], "]", \
              "(", _get_delta((bundle["start_date"], bundle["end_date"])).days, "days )")
        print("Members:")
        for member in bundle["members"]:
            print("\t", member["bed_id"], ": [", member["start_date"], "->", member["end_date"], "]")
        print()

def _run_with_timer(vacancies: List[Vacancy]) -> List[VacancyBundle]:
    start_time = time.perf_counter_ns()

    bundles = calc_vacancy_bundles(vacancies=vacancies)

    end_time = time.perf_counter_ns()
    elapsed_time_ms = (end_time - start_time) / 1000
    print(f"Elapsed time: {elapsed_time_ms:.0f}ms\n")

    return bundles

if __name__ == "__main__":
    print("Running Hearthmates Challenge...")

    #calc_vacancy_bundles(vacancies=trial_empty)
    bundles_0 = _run_with_timer(vacancies=_tuple_list_to_vacancies(trial_0))
    bundles_1 = _run_with_timer(vacancies=_tuple_list_to_vacancies(trial_1))
    bundles_2 = _run_with_timer(vacancies=_tuple_list_to_vacancies(trial_2))
    bundles_3 = _run_with_timer(vacancies=_tuple_list_to_vacancies(trial_3))
    bundles_4 = _run_with_timer(vacancies=_tuple_list_to_vacancies(trial_4))
    bundles_5 = _run_with_timer(vacancies=_tuple_list_to_vacancies(trial_5))
    bundles_6 = _run_with_timer(vacancies=_tuple_list_to_vacancies(trial_6))
    bundles_7 = _run_with_timer(vacancies=_tuple_list_to_vacancies(trial_7))

    if print_results:
        print("### Trial 0\n")
        _print_bundles(bundles_0)
        print("### Trial 1\n")
        _print_bundles(bundles_1)
        print("### Trial 2\n")
        _print_bundles(bundles_2)
        print("### Trial 3\n")
        _print_bundles(bundles_3)
        print("### Trial 4\n")
        _print_bundles(bundles_4)
        print("### Trial 5\n")
        _print_bundles(bundles_5)
        print("### Trial 6\n")
        _print_bundles(bundles_6)
        print("### Trial 7\n")
        _print_bundles(bundles_7)
