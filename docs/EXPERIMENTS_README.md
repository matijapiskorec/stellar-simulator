For the experiments we utilize Stellarbeat.io API (url)[(https://api.stellarbeat.io/docs/#/Network/getNetworkNodeSnapshots]. See the documentation for more details.

# Experiment Design Instructions for Stellar MAP Simulator  

## **Objective**  
The goal of these experiments is to observe the behavior of the Stellar MAP simulator under varying transaction loads and evaluate its impact on the inter-ledger finalization times.  

## **Experiment 1: Uniform Transaction Load**  

### **Overview**  
This experiment involves introducing a **uniform transaction load** over time. The number of transactions generated per unit of time remains constant, but this value is varied across different runs to measure its effect on ledger finalization times.

### **Steps**  

1. **Setup Simulation Parameters:**  
   - Ensure the simulator is calibrated to reproduce the empirical inter-ledger time of 6 seconds under a baseline transaction load.  
   - Set the parameters for a constant transaction arrival rate in the simulator's mempool.  

2. **Transaction Load Levels:**  
   - Define transaction arrival rates for multiple experiments, e.g.,  
     - **Baseline:** 100 transactions per second.  
     - **Increased Loads:** 150, 200, and 300 transactions per second.  

3. **Run the Simulation:**  
   - For each transaction load level, run the simulator for a sufficient duration to generate at least 10 finalized ledgers (e.g., 1 minute).  
   - Ensure that all other parameters (e.g., node topology, validator delays) remain consistent across runs.  

4. **Data Logging:**  
   - For each finalized ledger, log the following to a CSV file:  
     - Timestamp (seconds since simulation start).  
     - Number of transactions in the ledger.  
     - Ledger finalization time (time taken to finalize the ledger).  

5. **Analysis:**  
   - Construct a histogram of inter-ledger times for each transaction load level.  
   - Calculate summary statistics (mean, median, standard deviation) of inter-ledger times.  
   - Compare the results to the empirical data and analyze the relationship between transaction load and ledger finalization time.  

---

## **Experiment 2: Custom Experiment Design**  

### **Overview**  
The details of this experiment are not finalized and require further discussion. Initial ideas include simulating **bursts** of high transaction loads or experimenting with alternative configurations.  

---

## **File Output Structure**  

The CSV files generated during the experiments should have the following structure:  

| **Column**             | **Description**                              |  
|-------------------------|----------------------------------------------|  
| `timestamp`            | Number of seconds since the simulation start |  
| `ledger_id`            | Unique identifier for each finalized ledger  |  
| `transaction_count`    | Number of transactions in the finalized ledger |  
| `finalization_time`    | Time taken to finalize the ledger (seconds)  |  

---

## **Notes**  
- Ensure consistent simulation configurations across all experiments to maintain comparability.  
- Document any anomalies or unexpected behaviors observed during the runs.  
- Prepare preliminary plots (e.g., histograms, line charts) for presentation and further analysis.
