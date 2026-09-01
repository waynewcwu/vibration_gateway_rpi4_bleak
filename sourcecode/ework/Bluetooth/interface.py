import abc

class Toplayer(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def build_client(self,sid):
        return NotImplemented
    @abc.abstractmethod
    def del_client(self,sid):
        return NotImplemented
    @abc.abstractmethod
    def send(self,sid,i,data):
        return NotImplemented
