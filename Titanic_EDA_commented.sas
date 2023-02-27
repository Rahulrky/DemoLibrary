*Read Data From Flat File
proc import
datafile = "&path.titanic_train.csv"
out = titanic
dbms = csv;
run;

*View Summary Statistics
PROC MEANS DATA=titanic;
VAR _numeric_;
OUTPUT OUT=stats;
RUN;

*Summary Statistics By Group
PROC MEANS DATA=titanic;
CLASS Sex;
VAR _numeric_;
OUTPUT OUT=stats;
RUN;

*Change Column Names
data titanic2;
set titanic;
rename Pclass=passengerclass;
run;

*Drop Columns
data titanic2;
set titanic;
drop pclass;
run;

*Keep Columns
data titanic2;
set titanic;
keep pclass;
run;

*Add A New Column
proc sql noprint;
create table titanic2 as
select *,fare-mean(fare) as fare_deviation from titanic;
quit;

*Subset Data
data titanic2;
set titanic;
if sex='male';
keep Name Sex Pclass pclass;
run;

*Sort Data
proc sort data=titanic;
by descending passengerid;
run;

*Create two subsets from titanic data
data titanic_a(keep=passengerid name sex) titanic_b(keep=passengerid age survived);
set titanic;
if (passengerid in (887,888,889,890,891)) then output titanic_a;
if (passengerid in (884,885,886,887,888)) then output titanic_b;
run;

*Inner, Outer and Left Join
data titanic_inner titanic_left_a titanic_outer;
merge titanic_a (in = a)titanic_b (in = b);
by descending passengerid;
if a and b then output titanic_inner;
if a then output titanic_left_a;
if a or b then output titanic_outer;
run;

*Export Data
PROC EXPORT
DATA=titanic_outer
DBMS=csv
OUTFILE="&path.titanic_outer.csv";
run;