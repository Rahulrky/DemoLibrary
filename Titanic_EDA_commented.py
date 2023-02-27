import pandas as pd

#Read Data From Flat File
titanic=pd.read_csv('titanic_train.csv')

#View Summary Statistics
titanic.describe()

#Summary Statistics By Group
titanic.groupby('Sex').describe()

#Change Column Names
titanic2=titanic.rename(columns={'Pclass':'passengerclass'})

#Drop Columns
titanic2=titanic.drop(columns=['Pclass'])

#Keep Columns
titanic2=titanic[['Pclass']]

#Add A New Column
titanic['Fare_deviation']=titanic['Fare']-titanic['Fare'].mean()

#Subset Data
titanic2=titanic.loc[titanic['Sex']=='male',['Name','Sex','Pclass']]

#Sort Data
titanic.sort_values(by=['PassengerId'],ascending=False,inplace=True)

#Create two subsets from titanic data
titanic_a=titanic.loc[titanic['PassengerId'].isin([887,888,889,890,891]),['PassengerId','Name','Sex']]
titanic_b=titanic.loc[titanic['PassengerId'].isin([884,885,886,887,888]),['PassengerId','Age','Survived']]

#Inner, Outer and Left Join
titanic_inner=titanic_a.merge(titanic_b,how='inner',on='PassengerId')
titanic_left_a=titanic_a.merge(titanic_b,how='left',on='PassengerId')
titanic_outer=titanic_a.merge(titanic_b,how='outer',on='PassengerId')

#Export Data
titanic_outer.to_csv('titanic_outer.csv')