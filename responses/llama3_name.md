|   timestep | M                              | CM                            | AM                             | CAM                          | time taken                              |
|-----------:|:-------------------------------|:------------------------------|:-------------------------------|:-----------------------------|:----------------------------------------|
|     305000 | Next Region: 2                 | Next Region: 2                | Next Region: 2                 | Next Region: 2               | CAM: 0.85s M: 0.80s AM: 0.80s CM: 0.84s |
|            |                                | Region 1: Top Left            |                                | Region 1: Top Left           |                                         |
|            | Region 1: Top Left             | Region 2: Middle Left         | Region 1: Top Left             | Region 2: Top Right          |                                         |
|            | Region 2: Top Middle           | Region 3: Top Right           | Region 2: Top Middle           | Region 3: Bottom Right       |                                         |
|            | Region 3: Top Right            | Region 4: Bottom Right        | Region 3: Top Right            | Region 4: Bottom Left        |                                         |
|            | Region 4: Bottom               |                               | Region 4: Bottom               |                              |                                         |
|     605000 | Next Region: 8                 | Next Region: 6                | Next Region: 6                 | Next Region: 5               | M: 2.34s CAM: 2.24s CM: 2.32s AM: 2.36s |
|            |                                |                               | Region 1: Top-Left             |                              |                                         |
|            | Region 1: Top Left Corner      | Region 1: Top Left Corner     | Region 2: Top-Middle           | Region 1: Wall               |                                         |
|            | Region 2: Top Middle           | Region 2: Upper Right Corner  | Region 3: Top-Right            | Region 2: Upper Right        |                                         |
|            | Region 3: Top Right Corner     | Region 3: Upper Middle        | Region 4: Goal                 | Region 3: Upper Left         |                                         |
|            | Region 4: Goal Region          | Region 4: Goal                | Region 5: Bottom-Left          | Region 4: Goal               |                                         |
|            | Region 5: State Region         | Region 5: Bottom Left         | Region 6: Bottom-Middle        | Region 5: Bottom Left        |                                         |
|            | Region 6: Bottom Left Corner   | Region 6: Bottom Left Corner  | Region 7: Bottom-Right         | Region 6: Bottom Right       |                                         |
|            | Region 7: Ant's Current Region | Region 7: Bottom Middle       | Region 8: Not Found            | Region 7: Bottom             |                                         |
|            | Region 8: Narrow Path          | Region 8: Bottom Right Corner | Region 9: Not Found            | Region 8: Not Applicable     |                                         |
|            | Region 9: Wall Region          | Region 9: Bottom Right        | Region 10: Not Found           | Region 9: Not Applicable     |                                         |
|            | Region 10: Straight Path       | Region 10: Top Right          | Region 11: Bottom-Right Corner | Region 10: Top Right         |                                         |
|            | Region 11: Bottom Middle       | Region 11: Top Left           | Region 12: Not Found           | Region 11: Top               |                                         |
|            | Region 12: Bottom Right Corner | Region 12: Upper Right        |                                | Region 12: Not Applicable    |                                         |
|     930000 | Next Region: 15                | Next Region: 12               | Next Region: 11                | Next Region: 14              | M: 3.37s CM: 3.40s AM: 3.25s CAM: 3.74s |
|            |                                |                               |                                | Region 1: Region 5           |                                         |
|            | Region 1: Top Left Corner      | Region 1: Top Left Corner     | Region 1: Top Left Corner      | Region 2: Region 14          |                                         |
|            | Region 2: Top Middle           | Region 2: Top Middle          | Region 2: Not Available        | Region 3: Region 3           |                                         |
|            | Region 3: Top Right Corner     | Region 3: Top Right Corner    | Region 3: Not Available        | Region 4: Region 4           |                                         |
|            | Region 4: Goal Region          | Region 4: Goal                | Region 4: Goal Region          | Region 5: Region 5           |                                         |
|            | Region 5: Top Right            | Region 5: Bottom Left Corner  | Region 5: Top Middle           | Region 6: Region 6           |                                         |
|            | Region 6: Middle Left          | Region 6: Bottom Middle Left  | Region 6: Top Right            | Region 7: Region 7           |                                         |
|            | Region 7: Middle Middle        | Region 7: Bottom Middle       | Region 7: Not Available        | Region 8: Region 8           |                                         |
|            | Region 8: Middle Right         | Region 8: Bottom Middle Right | Region 8: Not Available        | Region 9: Region 9           |                                         |
|            | Region 9: Bottom Left          | Region 9: Bottom Right Corner | Region 9: Not Available        | Region 10: Region 10         |                                         |
|            | Region 10: Current Region      | Region 10: Middle Left        | Region 10: State Region        | Region 11: Region 11         |                                         |
|            | Region 11: Bottom Middle       | Region 11: Middle Right       | Region 11: Upper Middle        | Region 12: Region 12         |                                         |
|            | Region 12: Bottom Right        | Region 12: Bottom Middle      | Region 12: Not Available       | Region 13: Region 13         |                                         |
|            | Region 13: Bottom Right Corner | Region 13: Middle Right       | Region 13: Down Left           | Region 14: Region 14         |                                         |
|            | Region 14: Bottom Middle Left  | Region 14: Current Region     | Region 14: Current Region      | Region 15: Region 15         |                                         |
|            | Region 15: Next Region         | Region 15: Top Right          | Region 15: Down Middle         | Region 16: Region 16         |                                         |
|            | Region 16: Bottom Middle Right | Region 16: Bottom Right       | Region 16: Not Available       | Region 17: Region 17         |                                         |
|            | Region 17: Bottom Right Corner | Region 17: Bottom Right       | Region 17: Down Right          | Region 18: Region 18         |                                         |
|            | Region 18: Bottom Right Corner | Region 18: Bottom Left        | Region 18: Bottom Right        |                              |                                         |
|    4980000 | Next Region: 16                | Next Region: 18               | Next Region: 18                | Next Region: 18              | AM: 3.82s CM: 4.72s CAM: 4.27s M: 4.04s |
|            |                                |                               | Region 1: One                  | Region 1: Top Left Corner    |                                         |
|            | Region 1: Top Left Corner      | Region 1: Region 5            | Region 2: Two                  | Region 2: Top Right Corner   |                                         |
|            | Region 2: Top Edge             | Region 2: Region 6            | Region 3: Three                | Region 3: Upper Right        |                                         |
|            | Region 3: Top Right Corner     | Region 3: Region 7            | Region 4: Goal                 | Region 4: Goal               |                                         |
|            | Region 4: Goal                 | Region 4: Region 8            | Region 5: Five                 | Region 5: Bottom Left        |                                         |
|            | Region 5: Top Wall             | Region 5: Region 9            | Region 6: Six                  | Region 6: Bottom Left Corner |                                         |
|            | Region 6: First Gap            | Region 6: Region 10           | Region 7: Seven                | Region 7: Bottom Left Corner |                                         |
|            | Region 7: Second Gap           | Region 7: Region 11           | Region 8: Eight                | Region 8: Bottom Left        |                                         |
|            | Region 8: Wall                 | Region 8: Region 12           | Region 9: Nine                 | Region 9: Bottom Left        |                                         |
|            | Region 9: Narrow Path          | Region 9: Region 13           | Region 10: Ten                 | Region 10: Bottom Left       |                                         |
|            | Region 10: Wide Path           | Region 10: Region 14          | Region 11: Eleven              | Region 11: Bottom Left       |                                         |
|            | Region 11: T Junction          | Region 11: Region 15          | Region 12: Twelve              | Region 12: Bottom Left       |                                         |
|            | Region 12: Narrow Path         | Region 12: Region 16          | Region 13: Thirteen            | Region 13: Bottom Right      |                                         |
|            | Region 13: Wide Path           | Region 13: Region 17          | Region 14: Fourteen            | Region 14: Bottom Right      |                                         |
|            | Region 14: T Junction          | Region 14: Region 18          | Region 15: Fifteen             | Region 15: Bottom Right      |                                         |
|            | Region 15: Narrow Path         | Region 15: Region 19          | Region 16: Sixteen             | Region 16: Bottom Right      |                                         |
|            | Region 16: Path to Goal        | Region 16: Region 20          | Region 17: Seventeen           | Region 17: Bottom Right      |                                         |
|            | Region 17: Dead End            | Region 17: Region 21          | Region 18: Current             | Region 18: Current Region    |                                         |
|            | Region 18: State               | Region 18: Region 22          | Region 19: Nineteen            | Region 19: Upper Right       |                                         |
|            | Region 19: Wall                | Region 19: Region 23          | Region 20: Twenty              | Region 20: Bottom Right      |                                         |
|            | Region 20: Wide Path           | Region 20: Region 23          | Region 21: Twenty-One          | Region 21: Upper Right       |                                         |
|            | Region 21: Narrow Path         | Region 21: Region 23          | Region 22: Twenty-Two          | Region 22: Upper Right       |                                         |
|            | Region 22: Wide Path           | Region 22: Region 23          | Region 23: Twenty-Three        | Region 23: Upper Right       |                                         |
|            | Region 23: Dead End            | Region 23: Region 23          |                                |                              |                                         |