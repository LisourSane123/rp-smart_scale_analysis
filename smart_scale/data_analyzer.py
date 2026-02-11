import struct
from math import floor

class DataAnalyzer:
    def __init__(self, height, age, sex):
        self.height = height
        self.age = age
        self.sex = sex
        self.weight = 0
        self.impedance = 0

    def analyze(self, data):
        if data is None:
            print("Analysis failed: No data received.")
            return None

        # Basic validation of data length
        if len(data) < 13:
            print("Analysis failed: Invalid data packet.")
            return None

        self.impedance = ((data[10] & 0xFF) << 8) | (data[9] & 0xFF)
        self.weight = (((data[12] & 0xFF) << 8) | (data[11] & 0xFF)) / 200.0
        
        print(f"Received weight: {self.weight} kg, impedance: {self.impedance} ohm")

        # Check for potential out of boundaries
        if self.height > 220:
            print("Analysis failed: Height is too high (limit: >220cm)")
            return None
        elif self.weight < 10 or self.weight > 200:
            print("Analysis failed: Weight is out of range (limits: 10-200kg)")
            return None
        elif self.age > 99:
            print("Analysis failed: Age is too high (limit >99 years)")
            return None
        elif self.impedance > 3000:
            print("Analysis failed: Impedance is too high (limit >3000ohm)")
            return None

        return self.calculate_metrics()

    def calculate_metrics(self):
        lbm = self.getLBMCoefficient()
        fat_percentage = self.getFatPercentage()
        
        metrics = {
            "weight": round(self.weight, 2),
            "impedance": self.impedance,
            "lbm": round(lbm, 2),
            "fat_percentage": round(fat_percentage, 2),
            "water_percentage": round(self.getWaterPercentage(), 2),
            "bone_mass": round(self.getBoneMass(), 2),
            "muscle_mass": round(self.getMuscleMass(), 2),
            "visceral_fat": round(self.getVisceralFat(), 2),
            "bmi": round(self.getBMI(), 2),
            "bmr": round(self.getBMR(), 2),
            "ideal_weight": round(self.getIdealWeight(), 2),
            "metabolic_age": round(self.getMetabolicAge(), 2),
        }
        return metrics

    def checkValueOverflow(self, value, minimum, maximum):
        if value < minimum:
            return minimum
        elif value > maximum:
            return maximum
        else:
            return value

    def getLBMCoefficient(self):
        lbm = (self.height * 9.058 / 100) * (self.height / 100)
        lbm += self.weight * 0.32 + 12.226
        lbm -= self.impedance * 0.0068
        lbm -= self.age * 0.0542
        return lbm

    def getBMR(self):
        if self.sex == 'female':
            bmr = 864.6 + self.weight * 10.2036
            bmr -= self.height * 0.39336
            bmr -= self.age * 6.204
        else:
            bmr = 877.8 + self.weight * 14.916
            bmr -= self.height * 0.726
            bmr -= self.age * 8.976

        if self.sex == 'female' and bmr > 2996:
            bmr = 5000
        elif self.sex == 'male' and bmr > 2322:
            bmr = 5000
        return self.checkValueOverflow(bmr, 500, 10000)

    def getFatPercentage(self):
        LBM = self.getLBMCoefficient()

        if self.sex == 'female' and self.age <= 49:
            const = 9.25
        elif self.sex == 'female' and self.age > 49:
            const = 7.25
        else:
            const = 0.8

        if self.sex == 'male' and self.weight < 61:
            coefficient = 0.98
        elif self.sex == 'female' and self.weight > 60:
            coefficient = 0.96
            if self.height > 160:
                coefficient *= 1.03
        elif self.sex == 'female' and self.weight < 50:
            coefficient = 1.02
            if self.height > 160:
                coefficient *= 1.03
        else:
            coefficient = 1.0
        
        fatPercentage = (1.0 - (((LBM - const) * coefficient) / self.weight)) * 100

        if fatPercentage > 63:
            fatPercentage = 75
        return self.checkValueOverflow(fatPercentage, 5, 75)

    def getWaterPercentage(self):
        waterPercentage = (100 - self.getFatPercentage()) * 0.7
        coefficient = 1.02 if waterPercentage <= 50 else 0.98
        if waterPercentage * coefficient >= 65:
            waterPercentage = 75
        return self.checkValueOverflow(waterPercentage * coefficient, 35, 75)

    def getBoneMass(self):
        base = 0.245691014 if self.sex == 'female' else 0.18016894
        boneMass = (base - (self.getLBMCoefficient() * 0.05158)) * -1

        if boneMass > 2.2:
            boneMass += 0.1
        else:
            boneMass -= 0.1

        if self.sex == 'female' and boneMass > 5.1:
            boneMass = 8
        elif self.sex == 'male' and boneMass > 5.2:
            boneMass = 8
        return self.checkValueOverflow(boneMass, 0.5, 8)

    def getMuscleMass(self):
        muscleMass = self.weight - ((self.getFatPercentage() * 0.01) * self.weight) - self.getBoneMass()
        if self.sex == 'female' and muscleMass >= 84:
            muscleMass = 120
        elif self.sex == 'male' and muscleMass >= 93.5:
            muscleMass = 120
        return self.checkValueOverflow(muscleMass, 10, 120)

    def getVisceralFat(self):
        if self.sex == 'female':
            if self.weight > (13 - (self.height * 0.5)) * -1:
                subsubcalc = ((self.height * 1.45) + (self.height * 0.1158) * self.height) - 120
                subcalc = self.weight * 500 / subsubcalc
                vfal = (subcalc - 6) + (self.age * 0.07)
            else:
                subcalc = 0.691 + (self.height * -0.0024) + (self.height * -0.0024)
                vfal = (((self.height * 0.027) - (subcalc * self.weight)) * -1) + (self.age * 0.07) - self.age
        else:
            if self.height < self.weight * 1.6:
                subcalc = ((self.height * 0.4) - (self.height * (self.height * 0.0826))) * -1
                vfal = ((self.weight * 305) / (subcalc + 48)) - 2.9 + (self.age * 0.15)
            else:
                subcalc = 0.765 + self.height * -0.0015
                vfal = (((self.height * 0.143) - (self.weight * subcalc)) * -1) + (self.age * 0.15) - 5.0
        return self.checkValueOverflow(vfal, 1, 50)

    def getBMI(self):
        return self.checkValueOverflow(self.weight / ((self.height / 100) * (self.height / 100)), 10, 90)

    def getIdealWeight(self):
        if self.sex == 'female':
            return (self.height - 70) * 0.6
        else: # male
            return (self.height - 80) * 0.7

    def getMetabolicAge(self):
        if self.sex == 'female':
            metabolicAge = (self.height * -1.1165) + (self.weight * 1.5784) + (self.age * 0.4615) + (self.impedance * 0.0415) + 83.2548
        else:
            metabolicAge = (self.height * -0.7471) + (self.weight * 0.9161) + (self.age * 0.4184) + (self.impedance * 0.0517) + 54.2267
        return self.checkValueOverflow(metabolicAge, 15, 80)
