import unittest
from lib import espOnlineHandler


class espClassTest(unittest.TestCase):
    def test1(self):
        module1 = espOnlineHandler.esp("192.168.1.30", "AA")
        module2 = espOnlineHandler.esp("192.168.1.31", "AA")
        self.assertNotEqual(module1==module2, True)
    def test2(self):
        module1 = espOnlineHandler.esp("192.168.1.30", "AA")
        self.assertEqual(str(module1), "unknownModule 192.168.1.30")
    def test3(self):
        module1 = espOnlineHandler.esp("192.168.1.30", "MIC_THP_AA:BB:CC:DD:EE:FF")
        self.assertEqual(str(module1), "THP AA:BB:CC:DD:EE:FF")
    def test4(self):
        module1 = espOnlineHandler.esp("192.168.1.30", "ESP_2BAA76")
        self.assertEqual(str(module1), "ESP_2BAA76 192.168.1.30")

class espOnlineTest(unittest.TestCase):
    def setUp(self):
        self.handler = espOnlineHandler.espOnline()
        self.module1 = espOnlineHandler.esp("192.168.1.30", "MIC_THP_AA:BB:CC:DD:EE:FF")
        self.handler.addNew(self.module1)
    
    def test1(self):
        moduleList = self.handler.getModules()
        self.assertEqual(moduleList, [self.module1])
    
    def test2(self):
        module2 = espOnlineHandler.esp("192.168.1.30", "MIC_M2E_AA:BB:CC:DD:EE:FF")
        self.handler.addNew(module2)
        moduleList = self.handler.getModules()
        self.assertEquals(module2 in moduleList, True )
        self.assertEquals(self.module1 in moduleList, False)

if __name__ == "__main__":
    unittest.main()