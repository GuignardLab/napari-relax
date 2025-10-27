# Blind Comparison of Lineages

By calculating the distance between two lineages, users can identify which lineages or sublineages are similar or dissimilar. Manually selecting pairs for comparison can be tedious and time-consuming.  
This guide demonstrates how to **automatically compare every possible pair of lineages** to reveal clusters of similar lineages.

---

### 1. Select Timepoints

![config_1](./config_1.png){ width="300" }

Define the range of timepoints from which sublineages will be analyzed.  
For a blind search, it is recommended to start from the beginning of the dataset and stop at a timepoint where cell divisions are still occurring.

---

### 2. Crop the Dataset

![config_2](./config_2.png){ width="300" }

Lineages result from tracking, which depends heavily on data quality. In some cases, certain lineages are tracked more accurately than others.  
Because UTED is sensitive to differences in tree size, unequal tracking quality can lead to unreliable results.  
To minimize this, **crop the dataset** at a timepoint where most lineages of interest are still active and have not yet stopped dividing.

---

### 3. Select a Distance Style

![config_3](./config_3.png){ width="300" }

Choose the method for distance calculation.  
For blind discovery of similar lineages, the **`Reduced`** or **`Normalized Reduced`** styles are highly recommended.

---

### 4. Select Roots

![config_4](./config_4.png){ width="300" }

If you wish to compare sublineages from specific roots, select those roots by left-clicking on them.  
To include all roots in the analysis, select one root and press **Ctrl + A** to highlight them all.

---

### 5. Run the Comparison

![config_5](./config_5.png){ width="300" }

Start the process by clicking **Run Comparisons**.  
The tool will calculate distances between all possible lineage pairs within the selected parameters.

---

### 6. Inspect the Results

![clustermap_1](./clustermap_1.png){ width="300" }

Examine the resulting clustermap to identify potential clusters of similar lineages.  
Experiment with different colormaps and normalization settings to highlight meaningful patterns and refine the results.

---

### 7. Explore the Clustermap

![clustermap_2](./clustermap_2.png){ width="600" }

Click on an interesting cell in the clustermap (at any timepoint) to view how the corresponding sublineages contribute to the overall morphology.  
Repeat this step as many times as needed to explore different relationships.

---

### 8. (Optional) Save the Comparisons

![clustermap_3](./clustermap_3.png){ width="600" }

Save any interesting comparison results for further analysis using external data analysis tools or libraries.
