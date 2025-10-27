By calculating the distance between two lineages the user can find lineages and sublineaegs that are similar and disimilar. However, selecting lineages to compare manually is a long process, thus this guide will show how to blindly compare every possible pair to find clusters of similar lineages.

---
### 1. Select timepoints:

![config_1](./config_1.png)

Set the range of timepoints, where all sub/-lineages that spawn from the specified timepoints. For blind searching the user should select the start of the dataset and set stop to a timepoint where there are still division after it.

### 2. Crop the dataset:

![config_2](./config_2.png)

Lineages are products of tracking and tracking is dependant on the data quality. Thus sometimes some lineaegs are not as well tracked as others. UTED is very susceptible to wrong tree sizes, thus having two lineages, where the tracking quality is unequal will produce inaccurate results. Thus it is recommended to crop the dataset if needed. (For cropping find a timepoint where almost no lineage of interest has stopped.)

### 3. Style Selection:

![config_3](./config_3.png)

Select any style to use for calculating the distance. ```Reduced``` or ```normalized reduced``` are highly recommended, for blindly discovering similar lineages.

### 4. Selecting roots:

![config_4](./config_4.png)

If the user wants to find similar sublineages of specific roots, select all the roots of interest by left clicking on them. Otherwise select one and press Ctrl+A to slect them all.

### 5. Start comparing

~[config_5](./config_5.png)

Begin comparing by pressing ```Run Comparisons```.