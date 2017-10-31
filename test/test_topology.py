from io import StringIO

from twisted.trial import unittest

from opennsa import nsa, error, constants as cnt
from opennsa.topology import nml, nrm
from . import topology


LABEL = nsa.Label(cnt.ETHERNET_VLAN, '1781-1789')

ARUBA_NETWORK    = 'aruba:topology'
BONAIRE_NETWORK  = 'bonaire:topology'
CURACAO_NETWORK  = 'curacao:topology'
DOMINICA_NETWORK = 'dominica:topology'

ARUBA_PS   = nsa.STP(ARUBA_NETWORK,   'ps',   LABEL)
BONAIRE_PS = nsa.STP(BONAIRE_NETWORK, 'ps', LABEL)
CURACAO_PS = nsa.STP(CURACAO_NETWORK, 'ps', LABEL)


class TopologyTest(unittest.TestCase):

    def setUp(self):
        an,_ = nrm.parseTopologySpec(StringIO(topology.ARUBA_TOPOLOGY),    ARUBA_NETWORK)
        bn,_ = nrm.parseTopologySpec(StringIO(topology.BONAIRE_TOPOLOGY),  BONAIRE_NETWORK)
        cn,_ = nrm.parseTopologySpec(StringIO(topology.CURACAO_TOPOLOGY),  CURACAO_NETWORK)
        dn,_ = nrm.parseTopologySpec(StringIO(topology.DOMINICA_TOPOLOGY), DOMINICA_NETWORK)

        a_nsa = nsa.NetworkServiceAgent('aruba:nsa',    'a-endpoint')
        b_nsa = nsa.NetworkServiceAgent('bonaire:nsa',  'b-endpoint')
        c_nsa = nsa.NetworkServiceAgent('curacao:nsa',  'c-endpoint')
        d_nsa = nsa.NetworkServiceAgent('dominica:nsa', 'd-endpoint')

        self.networks = [ an, bn, cn, dn ]
        self.nsas     = [ a_nsa, b_nsa, c_nsa, d_nsa ]
        self.topology = nml.Topology()

        for network, nsi_agent in zip(self.networks, self.nsas):
            self.topology.addNetwork(network, nsi_agent)


    def testBasicPathfinding(self):

        # just the basic stuff and bandwidth, no structural tests

        paths = self.topology.findPaths(ARUBA_PS, BONAIRE_PS, 100)
        self.assertEqual(len(paths), 3)

        lengths = [ len(path) for path in paths ]
        self.assertEqual(lengths, [2,3,4])

        # test bandwidth - bw currently not in pathfinding
        #paths = self.topology.findPaths(ARUBA_PS, BONAIRE_PS, 300)
        #self.assertEquals(len(paths), 2)
        #paths = self.topology.findPaths(ARUBA_PS, BONAIRE_PS, 800)
        #self.assertEquals(len(paths), 1)

    testBasicPathfinding.skip = 'NML module is not used'

    def testNoSwapPathfinding(self):

        paths = self.topology.findPaths(ARUBA_PS, BONAIRE_PS, 100)
        self.assertEqual(len(paths), 3)

        first_path = paths[0]
        self.assertEqual(len(first_path), 2) # aruba - bonaire
        self.assertEqual( [ l.network for l in first_path ], [ARUBA_NETWORK, BONAIRE_NETWORK] )

        fpl = nsa.Label(cnt.ETHERNET_VLAN, '1781-1789')
        for link in first_path:
            self.assertEqual(link.src_label, fpl)
            self.assertEqual(link.dst_label, fpl)


        second_path = paths[1]
        self.assertEqual(len(second_path), 3) # aruba - dominica - bonaire
        self.assertEqual( [ l.network for l in second_path ], [ARUBA_NETWORK, DOMINICA_NETWORK, BONAIRE_NETWORK] )

        spl = nsa.Label(cnt.ETHERNET_VLAN, '1781-1782')
        for link in second_path:
            self.assertEqual(link.src_label, spl)
            self.assertEqual(link.dst_label, spl)


        third_path = paths[2]
        self.assertEqual(len(third_path), 4) # aruba - dominica - curacao - bonaire
        self.assertEqual( [ l.network for l in third_path ], [ARUBA_NETWORK, DOMINICA_NETWORK, CURACAO_NETWORK, BONAIRE_NETWORK] )

        tpl = nsa.Label(cnt.ETHERNET_VLAN, '1783-1786')
        for link in third_path:
            self.assertEqual(link.src_label, tpl)
            self.assertEqual(link.dst_label, tpl)

    testNoSwapPathfinding.skip = 'NML module is not used'


    def testFullSwapPathfinding(self):

        # make all networks capable of label swapping
        for nw in self.networks:
            nw.canSwapLabel = lambda _ : True

        paths = self.topology.findPaths(ARUBA_PS, BONAIRE_PS, 100)
        self.assertEqual(len(paths), 3)

        fp = paths[0]
        self.assertEqual(len(fp), 2) # aruba - bonaire
        self.assertEqual( [ l.network for l in fp ], [ARUBA_NETWORK, BONAIRE_NETWORK] )

        tpl = nsa.Label(cnt.ETHERNET_VLAN, '1781-1789')
        ipl = nsa.Label(cnt.ETHERNET_VLAN, '1780-1789')

        self.assertEqual(fp[0].src_label, tpl)
        self.assertEqual(fp[0].dst_label, ipl)
        self.assertEqual(fp[1].src_label, ipl)
        self.assertEqual(fp[1].dst_label, tpl)

        del fp, tpl, ipl

        sp = paths[1]
        self.assertEqual(len(sp), 3) # aruba - dominica - bonaire
        self.assertEqual( [ l.network for l in sp ], [ARUBA_NETWORK, DOMINICA_NETWORK, BONAIRE_NETWORK] )

        tpl = nsa.Label(cnt.ETHERNET_VLAN, '1781-1789')
        ipl = nsa.Label(cnt.ETHERNET_VLAN, '1780-1789')
        jpl = nsa.Label(cnt.ETHERNET_VLAN, '1781-1782')

        self.assertEqual(sp[0].src_label, tpl)
        self.assertEqual(sp[0].dst_label, ipl)
        self.assertEqual(sp[1].src_label, ipl)
        self.assertEqual(sp[1].dst_label, jpl)
        self.assertEqual(sp[2].src_label, jpl)
        self.assertEqual(sp[2].dst_label, tpl)

        del sp, tpl, ipl, jpl

        tp = paths[2]
        self.assertEqual(len(tp), 4) # aruba - dominica - curacao - bonaire
        self.assertEqual( [ l.network for l in tp ], [ARUBA_NETWORK, DOMINICA_NETWORK, CURACAO_NETWORK, BONAIRE_NETWORK] )

        tpl = nsa.Label(cnt.ETHERNET_VLAN, '1781-1789')
        ipl = nsa.Label(cnt.ETHERNET_VLAN, '1780-1789')
        jpl = nsa.Label(cnt.ETHERNET_VLAN, '1783-1786')
        kpl = nsa.Label(cnt.ETHERNET_VLAN, '1780-1789')

        self.assertEqual(tp[0].src_label, tpl)
        self.assertEqual(tp[0].dst_label, ipl)
        self.assertEqual(tp[1].src_label, ipl)
        self.assertEqual(tp[1].dst_label, jpl)
        self.assertEqual(tp[2].src_label, jpl)
        self.assertEqual(tp[2].dst_label, kpl)
        self.assertEqual(tp[3].src_label, kpl)
        self.assertEqual(tp[3].dst_label, tpl)

    testFullSwapPathfinding.skip = 'NML module is not used'


    def testPartialSwapPathfinding(self):

        # make bonaire and dominica capable of swapping label
        self.networks[1].canSwapLabel = lambda _ : True
        self.networks[3].canSwapLabel = lambda _ : True

        paths = self.topology.findPaths(ARUBA_PS, BONAIRE_PS, 100)
        self.assertEqual(len(paths), 3)

        fp = paths[0]
        self.assertEqual(len(fp), 2) # aruba - bonaire
        self.assertEqual( [ l.network for l in fp ], [ARUBA_NETWORK, BONAIRE_NETWORK] )

        tpl = nsa.Label(cnt.ETHERNET_VLAN, '1781-1789')

        self.assertEqual(fp[0].src_label, tpl)
        self.assertEqual(fp[0].dst_label, tpl)
        self.assertEqual(fp[1].src_label, tpl)
        self.assertEqual(fp[1].dst_label, tpl)

        del fp, tpl

        sp = paths[1]
        self.assertEqual(len(sp), 3) # aruba - dominica - bonaire
        self.assertEqual( [ l.network for l in sp ], [ARUBA_NETWORK, DOMINICA_NETWORK, BONAIRE_NETWORK] )

        tpl = nsa.Label(cnt.ETHERNET_VLAN, '1781-1789')
        ipl = nsa.Label(cnt.ETHERNET_VLAN, '1781-1782')

        self.assertEqual(sp[0].src_label, tpl)
        self.assertEqual(sp[0].dst_label, tpl)
        self.assertEqual(sp[1].src_label, tpl)
        self.assertEqual(sp[1].dst_label, ipl)
        self.assertEqual(sp[2].src_label, ipl)
        self.assertEqual(sp[2].dst_label, tpl)

        del sp, tpl, ipl

        tp = paths[2]
        self.assertEqual(len(tp), 4) # aruba - dominica - curacao - bonaire
        self.assertEqual( [ l.network for l in tp ], [ARUBA_NETWORK, DOMINICA_NETWORK, CURACAO_NETWORK, BONAIRE_NETWORK] )

        tpl = nsa.Label(cnt.ETHERNET_VLAN, '1781-1789')
        ipl = nsa.Label(cnt.ETHERNET_VLAN, '1781-1789')
        jpl = nsa.Label(cnt.ETHERNET_VLAN, '1783-1786')

        self.assertEqual(tp[0].src_label, tpl)
        self.assertEqual(tp[0].dst_label, ipl)
        self.assertEqual(tp[1].src_label, ipl)
        self.assertEqual(tp[1].dst_label, jpl)
        self.assertEqual(tp[2].src_label, jpl)
        self.assertEqual(tp[2].dst_label, jpl)
        self.assertEqual(tp[3].src_label, jpl)
        self.assertEqual(tp[3].dst_label, tpl)

    testPartialSwapPathfinding.skip = 'NML module is not used'

    def testNoAvailableBandwidth(self):
        self.assertRaises(error.BandwidthUnavailableError, self.topology.findPaths, ARUBA_PS, BONAIRE_PS, 1200)

    testNoAvailableBandwidth.skip = 'Bandwidth currently not available in path finding'

