import pandas as pd

titanic=pd.read_csv('titanic_train.csv')

titanic.describe()

titanic.groupby('Sex').describe()

titanic2=titanic.rename(columns={'Pclass':'passengerclass'})

titanic2=titanic.drop(columns=['Pclass'])
titanic2=titanic[['Pclass']]

titanic['Fare_deviation']=titanic['Fare']-titanic['Fare'].mean()

titanic2=titanic.loc[titanic['Sex']=='male',['Name','Sex','Pclass']]

titanic.sort_values(by=['PassengerId'],ascending=False,inplace=True)

titanic_a=titanic.loc[titanic['PassengerId'].isin([887,888,889,890,891]),['PassengerId','Name','Sex']]
titanic_b=titanic.loc[titanic['PassengerId'].isin([884,885,886,887,888]),['PassengerId','Age','Survived']]

titanic_inner=titanic_a.merge(titanic_b,how='inner',on='PassengerId')
titanic_left_a=titanic_a.merge(titanic_b,how='left',on='PassengerId')
titanic_outer=titanic_a.merge(titanic_b,how='outer',on='PassengerId')

titanic_outer.to_csv('titanic_outer.csv')