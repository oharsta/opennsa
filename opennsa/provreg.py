"""
Registry for tracking providers dynamically in OpenNSA.

Keeping track of providers in a dynamical way in an NSI implementation is a
huge pain in the ass. This is a combination of things, such as seperate
identities and endpoints, callbacks, and the combination of local providers.

The class ProviderRegistry tries to keep it a bit sane.
"""

from twisted.python import log

from opennsa import error

LOG_SYSTEM = 'providerregistry'


class ProviderRegistry(object):

    def __init__(self, providers, provider_factories):
        # usually initialized with local providers
        self.providers = providers.copy()
        self.provider_factories = provider_factories # { provider_type : provider_spawn_func }
        self.provider_networks = {} # { provider_urn : [ network ] }


    def getProvider(self, nsi_agent_urn):
        """
        Get a provider from a NSI agent identity/urn.
        """
        try:
            return self.providers[nsi_agent_urn]
        except KeyError:
            raise error.STPResolutionError('Could not resolve a provider for %s' % nsi_agent_urn)


    def getProviderByNetwork(self, network_id):
        """
        Get the provider urn by specifying network.
        """
        for provider, networks in list(self.provider_networks.items()):
            if network_id in networks:
                return provider
        else:
            raise error.STPResolutionError('Could not resolve a provider for %s' % network_id)


    def addProvider(self, nsi_agent_urn, provider, network_ids):
        """
        Directly add a provider. Probably only needed by setup.py
        """
        if not nsi_agent_urn in self.providers:
            log.msg('Creating new provider for %s' % nsi_agent_urn, system=LOG_SYSTEM)

        self.providers[ nsi_agent_urn ] = provider
        self.provider_networks[ nsi_agent_urn ] = network_ids


    def spawnProvider(self, nsi_agent, network_ids):
        """
        Create a new provider, from an NSI agent.
        ServiceType must exist on the NSI agent, and a factory for the type available.
        """
        if nsi_agent.urn() in self.providers and self.provider_networks[nsi_agent.urn()] == network_ids:
            log.msg('Skipping provider spawn for %s (no change)' % nsi_agent, debug=True, system=LOG_SYSTEM)
            return self.providers[nsi_agent.urn()]

        factory = self.provider_factories[ nsi_agent.getServiceType() ]
        prov = factory(nsi_agent)

        self.addProvider(nsi_agent.urn(), prov, network_ids)

        log.msg('Spawned new provider for %s' % nsi_agent, system=LOG_SYSTEM)

        return prov

