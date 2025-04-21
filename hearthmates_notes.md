# Thinking

Assume hostel has 10 rooms. Each room has an occupied or vacancy status which translates to a calendar of bools. So the hostel has 10 calendars of vacancies to manage.

The script I'm tasked with making should report the longest time frame of occupancy for 1, 2, 3, ... 10 folks?

"Groups of N young travelers book their stay at a single hostel"

"For every hostel with up to N vacant beds (each with an associated booking availability date pair), they will store in their database bundles of size [1, 2, …, i, …,  (N-1), N] that could be constructed with overlapping bed vacancies."

Each item above is a bed (ID) and dates (W)? AKA a Vacancy (V).

It's easier to think of this with a time range, so how about the next 30 days.

So they are bundling those Vacancies together where 1, 2, 3, N available beds exist simultaneously, where every time frame is a separate entry.

The individual availabilities may be different from the bundle window. Hence the "O" occupancy window.

I think to generate these, you combinatorics your way through all bed combos. n^2?

5 beds 2 bundle = 1&2, 1&3, 1&4, 1&5, 2&3, 2&4, 2&5, 3&4, 3&5, 4&5 = 10 combos (5 choose 2?)

https://www.statskingdom.com/combinations-calculator.html

n! / ((n-r)! * r!) [n beds, r group size]

For 100 beds choose 2, that's 4,950
For 100 beds choose 5, that's 75,287,520

Intuitively it looks like the closer the choose is to the total, the bigger the # combos it'll be. Usually it won't be except for big groups, which do happen.

So we definitely want to not do brute-force in order to save time. That will bring in cleverness and creativity that is probably what's of interest here.

Okay, and a "Vacancy Bundle" is explicitly defined as "the largest date range you could construct" with "d" degree (# beds/availabilities). So that's all we report from our algorithm?

Yeah: "store only the vacancy bundle with the widest availability date"

Goal: "calculate these vacancy bundles" !!!

## Visual

```
 	 		========	;
========				;
============			;
		============	;
	============		;
====			====	;
```

# Results

* Trial 0 - extra N=4 of 13 days
* Trial 1 - extra N=4,5 of 21, 17 days
* Trial 2 - different N=3,4
* Trial 3 - different N=3, extra N=6 of 22 days
* Trial 4 - missing N=5 of 52 days
* Trial 5 - extra N=4 of 20 days
* Trial 6 - different N=3,5
* Trial 7 - extra N=4

# Big O

n * ((n) + n*(3n/2) + n*(#)) -> n^2 * (1 + 3n/2 + #) -> n^3

# Questions

* Travellers usually have firm dates in mind, so max hostel occupancy time for N beds doesn't quite match their expectations?

# Conclusion & Learnings

* Rejection!
* This was a "[knapsack problem](https://en.wikipedia.org/wiki/Knapsack_problem)"
* A core mistake was assuming that the longest N bundle MUST be based on an N-1 bundle; this is apparently not true!
    * I'd love to generate an example that shows this clearly
* Imagine a graph of all vacancy bundles minus those culled; you can still build upon prior work for efficiency
* Vacancy storage and comparisons could have been done with a hashmap

# Form & Instructions

https://docs.google.com/forms/d/1UuDr0Br_usP4c7jb4alUuZ4F16PY9IwD6J_bgc2Ilhg/viewform?edit_requested=true

# Good Luck
