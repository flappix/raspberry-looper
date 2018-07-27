BUNDLE = a-delay.lv2
INSTALL_DIR = /usr/local/lib/lv2


$(BUNDLE): manifest.ttl a-delay.so
	rm -rf $(BUNDLE)
	mkdir $(BUNDLE)
	cp manifest.ttl a-delay.so $(BUNDLE)

a-delay.so: a-delay.cpp
	g++ -g -shared -fPIC -DPIC a-delay.cpp `pkg-config --cflags --libs lv2-plugin` -o a-delay.so

install: $(BUNDLE)
	mkdir -p $(INSTALL_DIR)
	rm -rf $(INSTALL_DIR)/$(BUNDLE)
	cp -R $(BUNDLE) $(INSTALL_DIR)
	cp manifest.ttl $(INSTALL_DIR)/a-delay.lv2/manifest.ttl
	cp a-delay.ttl $(INSTALL_DIR)/a-delay.lv2/a-delay.ttl
	cp presets.ttl $(INSTALL_DIR)/a-delay.lv2/presets.ttl

uninstall:
	rm -rf $(INSTALL_DIR)/$(BUNDLE)

clean:
	rm -rf $(BUNDLE) a-delay.so
